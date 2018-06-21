""" TODO """
import pathlib
import subprocess
import remu.util
from remu.remote import request
from remu.settings import config

class Nginx():
    """ TODO """
    def __init__(self):
        self.path = pathlib.Path(config['NGINX']['path'])

        self.rdp_maps = self.path.parent / 'rdp_maps.conf'
        if not self.rdp_maps.exists():
            with open(self.rdp_maps, "w"):
                pass

        self.rdp_upstreams = self.path.parent / 'rdp_upstreams.conf'
        if not self.rdp_upstreams.exists():
            with open(self.rdp_upstreams, "w"):
                pass

    def _reload(self):
        """Inform nginx to reload the configuration."""
        result = subprocess.check_output([str(self.path), "-s", "reload"])
        return result

    def add_mapping(self, session, server, ports):
        """ TODO """
        with self.rdp_maps.open("r+") as map_conf, self.rdp_upstreams.open("r+") as upstream_conf:
            mappings = list(map_conf)
            upstreams = list(upstream_conf)

            for port in ports:
                session_id = session + "_" + str(port)
                upstream = remu.util.rand_str(10)
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
        """ TODO """
        with self.rdp_maps.open("r+") as map_conf, self.rdp_upstreams.open("r+") as upstream_conf:
            mappings = list(map_conf)
            upstreams = list(upstream_conf)

            ups = [e.split()[1] for e in mappings if session in e]
            mappings = [e for e in mappings if session not in e]
            upstreams = [e for e in upstreams if e in ups]

            self.write_conf(map_conf, mappings)
            self.write_conf(upstream_conf, mappings)

            return True
        return False

    @classmethod
    def write_conf(cls, conf, mappings):
        """ TODO """
        conf.seek(0)
        for line in mappings:
            conf.write(line)
        conf.truncate()

class RemoteNginx():
    def __init__(self):
        self.ip = config['NGINX']['interface']
        self.port = config['NGINX']['port']

    def add_mapping(self, sid, server, ports):
        return request(self.ip, self.port, "add_mapping", session=sid, server=server, ports=ports)

    def remove_mapping(self, sid):
        return request(self.ip, self.port, "remove_mapping", session=sid)
