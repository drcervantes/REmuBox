import asyncio
import aiohttp
import logging
import json
from threading import Thread
from cryptography.fernet import Fernet
from urllib.parse import quote_plus

log = logging.getLogger(__name__)

key = b'ajkhUoSDyYDMGgARPrqdTR5JZRMz8S3YoNYgAwGkw8Q='
f = Fernet(key)

def build_url(ip, port, method, **kwargs):
	url_base = "http://{ip}:{port}/".format(ip=ip, port=port)
	query = "{}?".format(method)

	for k,v in kwargs.items():
		param = json.dumps(v)
		param = quote_plus(param)
		query += k + "=" + param + "&"

	enc_query = f.encrypt(query[:-1].encode())
	url = url_base + enc_query.decode()
	return url

async def _request_data(url):
	session = aiohttp.ClientSession()
	response = await session.get(url=url)
	content = await response.read()
	session.close()
	return content.decode("utf-8")

def request(url, worker, timeout=5):
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
		log.debug("Request to " + url + " timed out.")
		future.cancel()
	except Exception as e:
		log.error("The coroutine raised an exception: {!r}".format(e))
	else:
		return result

def _start_worker(loop):
	asyncio.set_event_loop(loop)
	loop.run_forever()

def create_worker():
	"""Create the new loop and worker thread."""
	worker_loop = asyncio.new_event_loop()
	worker = Thread(target=_start_worker, args=(worker_loop,))
	worker.start()
	return worker_loop

