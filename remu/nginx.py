""" TODO """
import pathlib
import subprocess
import logging

import remu.util
from remu.settings import config

l = logging.getLogger('default')

class Nginx():
    """ TODO """
    def __init__(self):
        self.path = pathlib.Path(config['NGINX']['path'])

        self.rdp_maps = self.path.parent / 'rdp_maps.conf'
        if not self.rdp_maps.exists():
            self.create_empty(self.rdp_maps)

        self.rdp_upstreams = self.path.parent / 'rdp_upstreams.conf'
        if not self.rdp_upstreams.exists():
            self.create_empty(self.rdp_upstreams)

        self._nginx_call("start")

    def clean_up(self):
        self.create_empty(self.rdp_maps)
        self.create_empty(self.rdp_upstreams)
        self._nginx_call("stop")

    def create_empty(self, path):
        with path.open(mode="w"):
            pass

    def _nginx_call(self, cmd):
        """Inform nginx to reload the configuration."""
        result = subprocess.check_output(["service", "nginx", cmd])
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
                l.info("New mapping: %s", new_map)
                mappings.append(new_map)
                self.write_conf(map_conf, mappings)

                new_upstream = "upstream " + upstream + " {server " + address + ";}\n"
                l.info("New upstream: %s", new_upstream)
                upstreams.append(new_upstream)
                self.write_conf(upstream_conf, upstreams)

            return True
        return False

    def remove_mapping(self, session):
        """ TODO """
        with self.rdp_maps.open("r+") as map_conf, self.rdp_upstreams.open("r+") as upstream_conf:
            l.info("Removing mapping for session: %s", session)
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
