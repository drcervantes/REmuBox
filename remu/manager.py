import string
import random
import logging

import remote
import db
import bson

log = logging.getLogger(__name__)

class Manager():
	def __init__(self, config=None, server=None, nginx=None):
		self.server = server
		self.nginx = nginx

		self.worker = remote.create_worker()

		connect('remu', host='127.0.0.1', port=27017)

		if server:
			self.server = server
			self.db.insert_server("127.0.0.1")

	def __del__(self):
		if self.server:
			self.db.remove_server("127.0.0.1")

	def start_session(self, workshop):
		"""Start a new session for a workshop participant.
		Returns a string containing a session id, the VRDE ports for the workshop unit, and the password
		associated with the session. """

		# Call load balancer to get server node and possible existing session
		server = self.load_balance(workshop)

		# Get the session
		session_id = self.obtain_session(server, workshop)
		self.start_session(server, session_id)

		session = self.db.get_session(session_id, server)

		# Add entries to NGINX
		self.add_nginx_entry(session_id, server, session['ports'])

		return session.to_json()

	def load_balance(self, workshop):
		"""Distributes the creation of workshop units across all server nodes available.

		The priority of server selection is as follows:
			1. A server has an available session (i.e. a workshop unit).
			2. The server with the least amount of running sessions.
		"""

		# Check if any servers have an available session
		servers = self.db.get_all_servers()
		if not bool(servers):
			log.error("Attempting to load balance with no servers!")
			return None

		for server in servers:
			if self.db.session_count_by_workshop(server['ip'], workshop, True) > 0:
				# TODO: Check if enough resources are available
				return server['ip']

		# Check if we can spawn a new session
		instances = 0
		for server in servers:
			instances += self.db.session_count_by_workshop(server['ip'], workshop)    	

		max_instances = self.db.get_workshop(workshop)['max_instances']
		if instances >= max_instances:
			log.debug("Maximum number of instances met or exceeded.")
			return None

		# Find server with least amount of workshops running
		sessions = 9999
		min_ip = ""
		for server in servers:
			count = self.db.session_count(server['ip'])
			if count < sessions:
				sessions = count
				min_ip = server['ip']
		return min_ip
		

	def obtain_session(self, server, workshop):
		"""Obtain a session for the specified workshop."""
		session, password = self.db.get_available_session(server, workshop)
		if session is not None:
			self.db.set_session_availability(workshop, session, False)
			return session, password

		session = str(bson.ObjectId())
		password = self.rand_str(6)
		self.db.insert_session(session, server, workshop, [], password, False)

		return session

	def start_session(self, server, session_id):
		session = self.db.get_session(session_id, server)
		if server == "127.0.0.1":
			# Workshop unit doesn't exist yet
			if not session['ports']:
				ports = self.server.clone_unit(workshop, session_id)
				self.db.update_session_ports(session_id, server, ports)
			self.server.start_unit(session_id)
		else:
			# We will be using a remote server
			server_port = self.db.get_server_port(server)
			if not session['ports']:
				url = remote.build_url(server, server_port, "clone_unit", workshop=workshop, session=session_id)
				ports = remote.request_data(url)
				self.db.update_session_ports(session_id, server, ports)
			url = remote.build_url(server, server_port, "start_unit", session=session_id)
			remote.request_data(url)


	def rand_str(self, length):
		return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(length))
	

	def add_nginx_entry(self, session, server, ports):
		if self.nginx:
			self.nginx.add_rdp_entry(session, server, ports)
		else:
			url = remote.build_url('192.168.1.2', 5000, "add_mapping", session=session, server=server, ports=ports)
			ports = remote.request(url, self.worker)

