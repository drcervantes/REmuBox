""" TODO """
import logging
import bson

from remu.remote import Remote
import remu.database as db
import remu.util

LOG = logging.getLogger(__name__)

class Manager():
    """ TODO """
    def __init__(self, config=None, server=None, nginx=None):
        self.server = server
        self.nginx = nginx
        self.config = config

        self.remote = Remote(config)

        if server:
            self.server = server
            db.insert_server("127.0.0.1", 9000)

    def __del__(self):
        if self.server:
            db.remove_server("127.0.0.1")

    def start_session(self, workshop):
        """
        Start a new session for a workshop participant.
        Returns a string containing a session id, the VRDE ports for the workshop unit,
        and the password associated with the session.
        """

        # Call load balancer to get server node and possible existing session
        server = self.load_balance(workshop)

        # Get the session
        session_id = self.obtain_session(server, workshop)
        self.start_unit(server, workshop, session_id)

        session = db.get_session(session_id, server)

        # Add entries to NGINX
        if self.nginx:
            self.nginx.add_mapping(session_id, server, session['ports'])
        else:
            host = self.config['NGINX']['host']
            port = self.config['NGINX']['port']
            url = self.remote.build_url(
                host,
                port,
                "add_mapping",
                session=session_id,
                server=server,
                ports=session['ports']
            )
            self.remote.request(url)

        return session.to_json()

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
            LOG.error("Attempting to load balance with no servers!")
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
            LOG.debug("Maximum number of instances met or exceeded.")
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

        sid = str(bson.ObjectId())
        password = remu.util.rand_str(int(self.config['REMU']['pass_len']))
        db.insert_session(server, sid, workshop, password, False)

        return session

    def start_unit(self, server, workshop, session_id):
        """ TODO """

        # THIS NEEDS TO BE REWORKED
        # EXISTENCE SHOULDNT DEPEND ON PORTS
        # MAYBE CHECK IF THERE ARE NO MACHINES????
        session = db.get_session(server, session_id)
        if server == "127.0.0.1":
            # Workshop unit doesn't exist yet
            if not session.machines:
                path = self.server.clone_unit(workshop, session_id)
                for machine in self.server.unit_to_str(path):
                    db.insert_machine(server, session_id, machine['name'], machine['port'])
            self.server.start_unit(session_id)
            
        else:
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

class Monitor():
    def __init__(self):
        print "probs do somethings here"
