from os.path import exists, join
import subprocess
import util

class Nginx():
	def __init__(self):
		self.path_to_nginx = 'C:\\Users\\Aegis\\Desktop'

		self.rdp_maps = join(self.path_to_nginx, 'rdp_maps.conf')
		if not exists(self.rdp_maps):
			with open(self.rdp_maps, "w"): pass
			
		self.rdp_upstreams = join(self.path_to_nginx, 'rdp_upstreams.conf')
		if not exists(self.rdp_upstreams):
			with open(self.rdp_upstreams, "w"): pass

	def reload(self):
		"""Inform nginx to reload the configuration."""
		result = subprocess.check_output(["nginx", "-s", "reload"])
 
	def add_mapping(self, session, server, ports):
		with open(self.rdp_maps, "r+") as map_conf, open(self.rdp_upstreams, "r+") as upstream_conf:
			mappings = list(map_conf)
			upstreams = list(upstream_conf)

			for port in ports:
				session_id = session + "_" + str(port)
				upstream = util.rand_str(10)
				address = server + ":" + str(port)

				new_map = session_id + " " + upstream + ";\n"
				mappings.append(new_map)
				self.write_conf(map_conf, mappings)

				new_upstream = "upstream " + upstream + " {server " + address + ";}\n"
				upstreams.append(new_upstream)
				self.write_conf(upstream_conf, upstreams)  

			return True
		return False

	def remove_mapping(self, session):
		with open(self.rdp_maps, "r+") as map_conf, open(self.rdp_upstreams, "r+") as upstream_conf:
			mappings = list(map_conf)
			upstreams = list(upstream_conf)

			u = [e.split()[1] for e in mappings if session in e]
			mappings = [e for e in mappings if session not in e]
			upstreams = [e for e in upstreams if e in u]

			self.write_conf(map_conf, mappings)
			self.write_conf(upstream_conf, mappings)

			return True
		return False

	def write_conf(self, conf, mappings):
		conf.seek(0)
		for line in mappings:
			conf.write(line)
		conf.truncate()

# n = Nginx()
# n.add_mapping('87ry2','127.0.0.1',[5000,5001])
# n.add_mapping('1d83a','127.0.0.1',[5002,5003])
# n.remove_mapping('87ry2')
# http://127.0.0.1:5000/add_mapping?session=%27%2287ry2%22%27&server=%27%22127.0.0.1%22%27&ports=%27[5000,5001]%27
# http://127.0.0.1:5000/add_mapping?session=%22ABCDE%22&server=%22127.0.0.1%22&ports=[5000%2C5001]