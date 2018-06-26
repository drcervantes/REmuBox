""" TODO """
import logging
import json
import urllib.parse
import cryptography.fernet as fernet
import requests

from remu.settings import config

l = logging.getLogger(__name__)

class RemoteComponent():
    def __init__(self, ip, port, modules):
        self.ip = ip
        self.port = port
        self.modules = modules

        self.fern = fernet.Fernet(config['REMU']['secret_key'].encode())

    def __getattr__(self, name):
        def get(self, **kwargs):
            if getattr(self.modules, name):
                return self._request(name, **kwargs)
        return get.__get__(self)

    def _build_url(self, method, **kwargs):
        """
        Construct an encrypted url for a remote request.
        """
        url_base = "http://{}:{}/".format(self.ip, self.port)
        query = "{}?".format(method)

        for arg, val in kwargs.items():
            param = json.dumps(val)
            param = urllib.parse.quote_plus(param)
            query += "{}={}&".format(arg, param)

        l.debug("URL prior to encryption: %s%s", url_base, query[:-1])
        enc_query = self.fern.encrypt(query[:-1].encode())
        url = url_base + enc_query.decode()
        return url

    def _request(self, method, **kwargs):
        url = self._build_url(method, **kwargs)
        try:
            r = requests.get(url)
            r.raise_for_status()
            return r.text
        except requests.exceptions.ConnectionError:
            l.exception("Error could not connect to %s:%d", self.ip, self.port)
        except requests.exceptions.HTTPError:
            l.exception("Error requesting %s from %s:%d", method, self.ip, self.port)
