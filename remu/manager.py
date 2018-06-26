""" TODO """
import logging
import gevent
import bson
import ast
import time

from remu.settings import config
import remu.database as db
import remu.util
import remu.remote
import remu.server

l = logging.getLogger('default')

class Manager():
    """ TODO """
    def __init__(self, local_server, nginx, local_monitor):
        l.info("Manager module starting...")

        self.nginx = nginx
        self.pm = local_monitor
        self.servers = {}

        if local_server:
            db.insert_server("127.0.0.1", 9000)
            self.servers["127.0.0.1"] = local_server

        # Create WorkshopManager objects for each server
        servers = db.get_all_servers()
        for s in servers:
            if s["ip"] != "127.0.0.1":
                self.register_remote_server(s["ip"], s["port"])

        self.monitor_thread = gevent.spawn(self.monitor_service)
        gevent.spawn(self.test)

    def test(self):
        time.sleep(10)
        self.start_workshop('Route_Hijacking')

    def clean_up(self):
        l.info(" ... Manager cleaning up")

        if "127.0.0.1" in self.servers:
            db.remove_server("127.0.0.1")

        self.monitor_thread.kill()

    def register_remote_server(self, ip, port):
        modules = [remu.server.WorkshopManager, remu.server.PerformanceMonitor]
        self.servers[ip] = remu.remote.RemoteComponent(ip, port, modules)

    def start_workshop(self, workshop):
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
        session_id = self.obtain_session(server, workshop)
        l.info("Using session: %s", session_id)

        self._run_workshop(server, workshop, session_id)

        vrde_ports = db.get_vrde_ports(server, session_id)

        # Add entries to NGINX
        # if self.nginx:
        #     self.nginx.add_mapping(session_id, server, vrde_ports)
        # else:
        #     host = self.config['NGINX']['host']
        #     port = self.config['NGINX']['port']
        #     url = self.remote.build_url(
        #         host,
        #         port,
        #         "add_mapping",
        #         session=session_id,
        #         server=server,
        #         ports=session['ports']
        #     )
        #     self.remote.request(url)

        return session_id

    @classmethod
    def load_balance(cls, workshop):
        """
        Distributes the creation of workshop units across all server nodes available.

        The priority of server selection is as follows:
            1. A server has an available session (i.e. a workshop unit).
            2. The server with the least amount of running sessions.
        """

        # Check if any servers have an available session
        servers = db.get_all_servers()
        if not bool(servers):
            l.error("Attempting to load balance with no servers!")
            return None

        for server in servers:
            if db.session_count_by_workshop(server['ip'], workshop, True) > 0:
                # TODO: Check if enough resources are available
                return server['ip']

        # Check if we can spawn a new session
        instances = 0
        for server in servers:
            instances += db.session_count_by_workshop(server['ip'], workshop)

        max_instances = db.get_workshop(workshop)['max_instances']
        if instances >= max_instances:
            l.error("Maximum number of instances met or exceeded.")
            return None

        # Find server with least amount of workshops running
        sessions = 9999
        min_ip = ""
        for server in servers:
            count = db.session_count(server['ip'])
            if count < sessions:
                sessions = count
                min_ip = server['ip']
        return min_ip

    def obtain_session(self, server, workshop):
        """Obtain a session for the specified workshop."""
        session, password = db.get_available_session(server, workshop)
        if session is not None:
            db.update_session(workshop, session, False)
            return session, password

        return self._create_session(server, workshop)

    def _create_session(self, server, workshop):
        session = self._create_session_id()
        password = self._create_password()
        db.insert_session(server, session, workshop, password)
        return session

    @classmethod
    def _create_session_id(cls):
        return str(bson.ObjectId())

    @classmethod
    def _create_password(cls):
        return remu.util.rand_str(int(config['REMU']['pass_len']))

    def _run_workshop(self, ip, workshop, session_id):
        """ TODO """
        server = self.servers[ip]
        session = db.get_session(ip, session_id)

        # Workshop unit doesn't exist yet
        if not session['machines']:
            server.clone_unit(workshop=workshop, session_id=session_id)

            for machine in server.unit_to_str(sid=session_id):
                db.insert_machine(ip, session_id, machine['name'], machine['port'])

        server.start_unit(sid=session_id)

    def stop_workshop(self, session_id):
        l.info("Stopping session: %s", session_id)

        server_data = db.get_server_from_session(session_id)
        ip = server_data['ip']

        server = self.servers[ip]
        server.stop_unit(sid=session_id)
        workshop = db.get_workshop_from_session(ip, session_id)
        db.remove_session(ip, session_id)

        # Get the current number of sessions for the workshop
        instances = db.session_count_by_workshop(ip, workshop['name'])
        l.info(" Current # of instances for %s: %d", workshop['name'], instances)

        # Ensure the minimum amount of sessions are met
        if instances < workshop['min_instances']:
            new_sid = self._create_session(ip, workshop)
            server.restore_unit(sid=session_id, new_sid=new_sid)
            for machine in server.unit_to_str(new_sid):
                db.insert_machine(ip, new_sid, machine['name'], machine['port'])
        else:
            # Remove machine
            server.remove_unit(sid=session_id)

    def _status_update(self, ip):
        if self.pm:
            status = self.pm.update()

        else:
            status = self.servers[ip].update()

            # Convert the status data from a string to a dictionary
            status = ast.literal_eval(status)

        db.update_server_status(ip, cpu=status["cpu"], mem=status["mem"], hdd=status["hdd"])

        for sid in status['sessions']:
            for m in status['sessions'][sid]:
                if "vrde-active" in m:
                    db.update_machine_status(ip, sid, active=m["vrde-active"])

    def monitor_service(self):
        # Sessions to be recycled after the timeout interval
        recycle = {}
        delay = int(config['REMU']['recycle_delay'])
        interval = int(config['REMU']['polling_interval'])

        while True:
            l.info("Sessions up for recycling: %s", str(recycle))
            # Update the status of the system
            jobs = [gevent.spawn(self._status_update(ip)) for ip in self.servers]
            gevent.joinall(jobs)

            # Get active sessions
            active = db.get_active_sessions()

            if active:
                # Check for active sessions with no active vrde connections
                for sid, session in active.items():
                    if not any([machine['active'] for machine in session['machines']]):
                        if sid not in recycle:
                            recycle[sid] = time.time()
                    else:
                        if sid in recycle:
                            del recycle[sid]

            # Check if any sessions have exceeded the delay
            if recycle:
                for sid, stime in recycle.copy().items():
                    now = time.time()
                    if now >= stime + delay:
                        self.stop_workshop(sid)
                        del recycle[sid]

            time.sleep(interval)
