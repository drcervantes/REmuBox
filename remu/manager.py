""" TODO """
import logging
import gevent
import bson
import time

from remu.settings import config
import remu.database as db
import remu.util
import remu.remote
import remu.server

l = logging.getLogger(config["REMU"]["logger"])

class Manager():
    """ TODO """
    def __init__(self, server, nginx, monitor):
        l.info("Manager module starting...")

        self.nginx = nginx
        self.pm = monitor
        self.servers = {}

        if server:
            db.insert_server("127.0.0.1", 9000)
            self.servers["127.0.0.1"] = server

        # Create WorkshopManager objects for each server
        servers = db.get_all_servers()
        for s in servers:
            if s["ip"] != "127.0.0.1":
                self.register_remote_server(s["ip"], s["port"])

        # Start sessions for min instances
        l.info("Starting minimum instances...")
        for w in db.get_all_workshops():
            for dummy in range(w["min_instances"]):
                self.start_workshop(w["name"], True)

        self.monitor_thread = gevent.spawn(self.monitor_service)

    def clean_up(self):
        l.info(" ... Manager cleaning up")

        if "127.0.0.1" in self.servers:
            db.remove_server("127.0.0.1")

        # TODO: remove session entries from all remote servers

        self.monitor_thread.kill()

    def register_remote_server(self, ip, port):
        modules = [remu.server.WorkshopManager, remu.server.PerformanceMonitor]
        self.servers[ip] = remu.remote.RemoteComponent(ip, port, modules)

    def start_workshop(self, workshop, available=False):
        """
        Start a new session for a workshop participant.
        Returns a string containing a session id, the VRDE ports for the workshop unit,
        and the password associated with the session.
        """

        l.info("Starting a %s workshop", workshop)

        # Call load balancer to get server node and possible existing session
        server = self.load_balance(workshop)
        if not server:
            l.info(" ... no suitable server found!")
            return None
        l.info("Load balancer selected: %s", server)

        # Get the session
        session_id = self.obtain_session(server, workshop, available)
        l.info("Using session: %s", session_id)

        self._build_workshop(server, workshop, session_id)
        if not available:
            self.servers[server].start_unit(sid=session_id)

        vrde_ports = db.get_vrde_ports(session_id)

        # Add entries to NGINX
        self.nginx.add_mapping(
            session=session_id,
            server=server,
            ports=vrde_ports
        )

        return ["{}_{}".format(session_id, port) for port in vrde_ports]

    @classmethod
    def load_balance(cls, workshop):
        """
        Distributes the creation of workshop units across all server nodes available.

        The priority of server selection is as follows:
            1. A server has an available session (i.e. a workshop unit).
            2. The server with the least amount of running sessions.
        """

        l.debug("Load balance for a %s workshop", workshop)

        # Check if any servers have an available session
        servers = db.get_all_servers()
        if not bool(servers):
            l.error("Attempting to load balance with no servers!")
            return None

        for server in servers:
            l.debug(" ... checking for available session at server: %s", server["ip"])

            count = db.session_count_by_workshop(workshop, server['ip'], True)
            l.debug(" ... found %d available", count)

            if count > 0:
                return server['ip']

        l.debug(" ... checking if we can spawn a new session")

        instances = 0
        for server in servers:
            instances += db.session_count_by_workshop(workshop, server['ip'])
        l.debug(" ... total instances for %s: %d", workshop, instances)

        max_instances = db.get_workshop(name=workshop)['max_instances']
        l.debug(" ... max instances allowed: %d", max_instances)
        if instances >= max_instances:
            l.error("Maximum number of instances met or exceeded.")
            return None

        # Find server with least amount of workshops running
        l.debug(" ... selecting server with least amount of workshops running")
        sessions = 9999
        min_ip = 0
        for i, server in enumerate(servers):
            count = db.session_count(server['ip'])
            if count < sessions:
                sessions = count
                min_ip = i

        # Finally ensure the server has enough resources
        server = servers[i]
        try:
            if server['mem'] < float(config['REMU']['mem_limit']) and \
               server['hdd'] < float(config['REMU']['hdd_limit']):
                return server['ip']
        except KeyError:
            l.warn(" ... making decision without hardware check!")
            return server['ip']

        l.error(" ... unable to find a suitable server!")
        return None

    def obtain_session(self, server, workshop, available):
        """Obtain a session for the specified workshop."""
        session = db.get_available_session(server, workshop)

        if session is None:
            session = self._create_session(server, workshop)

        if not available:
            db.update_session(server, session, available)

        return session

    def _create_session(self, server, workshop):
        session = self._create_session_id()
        password = self._create_password()
        db.insert_session(server, session, workshop, password)
        return session

    @classmethod
    def _create_session_id(cls):
        return remu.util.rand_str(int(config['REMU']['pass_len']))
        # return str(bson.ObjectId())

    @classmethod
    def _create_password(cls):
        return remu.util.rand_str(int(config['REMU']['pass_len']))

    def _build_workshop(self, ip, workshop, session_id):
        """ TODO """
        server = self.servers[ip]
        session = db.get_session(ip, session_id)

        # Workshop unit doesn't exist yet
        if not session['machines']:
            server.clone_unit(workshop=workshop, session_id=session_id)

            for machine in server.unit_to_str(sid=session_id):
                db.insert_machine(ip, session_id, machine['name'], machine['port'])

    def stop_workshop(self, session_id):
        l.info("Stopping session: %s", session_id)

        server_data = db.get_server_from_session(session_id)
        ip = server_data['ip']

        server = self.servers[ip]
        server.stop_unit(sid=session_id)
        workshop = db.get_workshop_from_session(ip, session_id)
        db.remove_session(ip, session_id)
        self.nginx.remove_mapping(session=session_id)

        # Get the current number of sessions for the workshop
        instances = db.session_count_by_workshop(ip, workshop['name'])
        l.info("Current # of instances for %s: %d", workshop['name'], instances)

        # Ensure the minimum amount of sessions are met
        if instances < workshop['min_instances']:
            new_sid = self._create_session(ip, workshop['name'])
            server.restore_unit(sid=session_id, new_sid=new_sid)
            for machine in server.unit_to_str(new_sid):
                db.insert_machine(ip, new_sid, machine['name'], machine['port'])
        else:
            # Remove machine
            server.remove_unit(sid=session_id)

    def _status_update(self, ip):
        l.debug("Getting status update for %s", ip)

        if ip == "127.0.0.1":
            status = self.pm.update()
        else:
            status = self.servers[ip].update()

        db.update_server(ip, cpu=status["cpu"], mem=status["mem"], hdd=status["hdd"])
        l.debug(" ... update: %s", str(status))

        for sid in status['sessions']:
            db.update_machines(ip, sid, status['sessions'][sid])

    def monitor_service(self):
        # Sessions to be recycled after the timeout interval
        recycle = {}
        delay = int(config['REMU']['recycle_delay'])
        interval = int(config['REMU']['polling_interval'])

        while True:
            gevent.sleep(interval)

            l.info("Sessions up for recycling: %s", str(recycle.keys()))
            # Update the status of the system
            jobs = [gevent.spawn(self._status_update(ip)) for ip in self.servers]
            gevent.joinall(jobs)

            # Get active sessions
            active = db.get_active_sessions()
            l.debug("Current active sessions: %s", str(active.keys()))

            if active:
                # Check for active sessions with no active vrde connections
                for sid, session in active.items():
                    if not any([machine['vrde_active'] for machine in session['machines']]):
                        if sid not in recycle:
                            l.debug("Adding to recycle, sid: %s", sid)
                            recycle[sid] = time.time()
                    else:
                        if sid in recycle:
                            l.debug("Session is now active, removing from recycle: %s", sid)
                            del recycle[sid]

            # Check if any sessions have exceeded the delay
            if recycle:
                for sid, stime in recycle.copy().items():
                    now = time.time()
                    if now >= stime + delay:
                        self.stop_workshop(sid)
                        del recycle[sid]
