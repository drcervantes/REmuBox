""" TODO """
import logging
import json
import threading
import urllib.parse
import asyncio
import aiohttp
from remu.settings import config

l = logging.getLogger(__name__)

fern = fernet.Fernet(config['REMU']['secret_key'].encode())

"""Create the new loop and worker thread."""
worker = threading.Thread(target=self._start_worker, args=(asyncio.new_event_loop(),))
worker.start()

def build_url(host, port, method, **kwargs):
    """
    Construct an encrypted url for a remote request.
    """
    url_base = "http://{}:{}/".format(host, port)
    query = "{}?".format(method)

    for arg, val in kwargs.items():
        param = json.dumps(val)
        param = urllib.parse.quote_plus(param)
        query += arg + "=" + param + "&"

    enc_query = fern.encrypt(query[:-1].encode())
    url = url_base + enc_query.decode()
    return url

async def _request_data(url):
    session = aiohttp.ClientSession()
    response = await session.get(url=url)
    content = await response.read()
    session.close()
    return content.decode("utf-8")

def request(surl, timeout=5):
    """Sends an http request asychronously so as to not block the manager web service.
    Used to communicate with the other subsystems.

    Args:
        url (str): URL string to the web service along with its arguments.
        timeout (int): Wait interval for the request.

    Returns:
        A string containing the result from the resulting web service view.
    """
    try:
        future = asyncio.run_coroutine_threadsafe(_request_data(url), worker)
        result = future.result(timeout)
    except asyncio.TimeoutError:
        l.debug("Request to %s timed out.", url)
        future.cancel()
    except Exception as exc:
        l.error("The coroutine raised an exception: %s", repr(exc))
    else:
        return result

def _start_worker(loop):
    """Worker routine for asynchronous http requests."""
    asyncio.set_event_loop(loop)
    loop.run_forever()
