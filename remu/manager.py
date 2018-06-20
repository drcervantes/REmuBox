""" TODO """
import logging
import bson

from remu.settings import config
import remu.database as db
import remu.util

l = logging.getLogger('default')

class Manager():
    """ TODO """
    def __init__(self, server=None, nginx=None):
        self.nginx = nginx
        self.server = server

        if server:
            db.insert_server("127.0.0.1", 9000)

        # s = self.start_workshop("Route_Hijacking")
        # self.stop_workshop(s)

    def __del__(self):
        if self.server:
            db.remove_server("127.0.0.1")

    def maybe(self):
        return True

    def start_workshop(self, workshop):
        """
        Start a new session for a workshop participant.
        Returns a string containing a session id, the VRDE ports for the workshop unit,
        and the password associated with the session.
        """

        l.info("Starting a %s workshop", workshop)

        # Call load balancer to get server node and possible existing session
        server = self.load_balance(workshop)
        l.info("Load balancer selected: %s", server)

        # Get the session
        session_id = self.obtain_session(server, workshop)
        l.info("Using session: %s", session_id)

        if server == "127.0.0.1":
            self._start_local(workshop, session_id)
        else:
            self._start_remote(server, workshop, session_id)

        vrde_ports = db.get_vrde_ports(server, session_id)
        l.info("Running on ports: %s", repr(vrde_ports))

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

        return session_id     # TODO: Make sure the return is what the view needs

    def stop_workshop(self, sid):
        self._stop_local(sid)

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

    def _create_session_id(self):
        return str(bson.ObjectId())

    def _create_password(self):
        return remu.util.rand_str(int(config['REMU']['pass_len']))

    def _start_local(self, workshop, session_id):
        """ TODO """
        session = db.get_session('127.0.0.1', session_id)

        # Workshop unit doesn't exist yet
        if not session['machines']:
            self.server.clone(workshop, session_id)
            for machine in self.server.unit_to_str(session_id):
                db.insert_machine('127.0.0.1', session_id, machine['name'], machine['port'])

        self.server.start(session_id)

    def _start_remote(self, server, workshop, session_id):
        """ TODO """
        server_port = db.get_server(server)['port']

        if not session['ports']:
            url = self.remote.build_url(
                server,
                server_port,
                "clone_unit",
                workshop=workshop,
                session=session_id
            )
            ports = self.remote.request(url)
            db.update_session_ports(session_id, server, ports)
        url = self.remote.build_url(server, server_port, "start_unit", session=session_id)
        self.remote.request(url)

    def _stop_local(self, session_id):
        l.debug("Stopping session: %s", session_id)
        self.server.stop(session_id)
        workshop = db.get_workshop_from_session("127.0.0.1", session_id)
        db.remove_session("127.0.0.1", session_id)

        # Get the current number of sessions for the workshop
        instances = db.session_count_by_workshop("127.0.0.1", workshop['name'])
        l.debug(" ... current # of instances: %d", instances)

        # Ensure the minimum amount of sessions are met
        if instances < workshop['min_instances']:
            new_sid = self._create_session("127.0.0.1", workshop)
            self.server.restore(session_id, new_sid)
            for machine in self.server.unit_to_str(new_sid):
                db.insert_machine('127.0.0.1', new_sid, machine['name'], machine['port'])
        else:
            # Remove machine
            l.debug("not ready")
