""" TODO """
import logging
import json
import urllib.parse
import cryptography.fernet as fernet
import requests

from remu.settings import config

l = logging.getLogger(__name__)

fern = fernet.Fernet(config['REMU']['secret_key'].encode())

def _build_url(host, port, method, **kwargs):
    """
    Construct an encrypted url for a remote request.
    """
    global fern
    url_base = "http://{}:{}/".format(host, port)
    query = "{}?".format(method)

    for arg, val in kwargs.items():
        param = json.dumps(val)
        param = urllib.parse.quote_plus(param)
        query += arg + "=" + param + "&"

    enc_query = fern.encrypt(query[:-1].encode())
    url = url_base + enc_query.decode()
    return url

def request(host, port, method, **kwargs):
    url = _build_url(host, port, method, **kwargs)
    try:
        r = requests.get(url)
        r.raise_for_status()
        return r.text
    except requests.exceptions.HTTPError:
        l.exception("Error requesting %s from %s:%d", method, host, port)
