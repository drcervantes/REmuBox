# The primary purpose of the gevent.monkey module is to carefully patch, in place, portions of the standard library 
# with gevent-friendly functions that behave in the same way as the original (at least as closely as possible).
import gevent
gevent.monkey.patch_all()

import gevent.pywsgi as wsgi
import cryptography.fernet as fernet
import urllib.parse as ulib
import flask
import argparse
import ast
import signal
import sys
import gc
import configparser

from remu.util import configure_logger


def create_app(config=None):
	"""Setup the Flask application to handle any remote service routine calls. This includes interaction
	between the modules when run remotely and the front-end."""
	app = flask.Flask('remu')

	app.config.update(dict(
		DEBUG=True,
		SECRET_KEY=b'_5#y2L"F4Q8z\n\xec]/'
	))
	app.config.update(config or {})

	@app.route('/<path:path>')
	def catch_all(path):
		if "favicon.ico" in path:
			return ""

		url = ulib.urlparse(flask.request.url)
		path = url.path[1:].encode()
		path = f.decrypt(path).decode()

		alog.debug("Received path: {}".format(url.path))

		method, params = path.split('?')
		params = ulib.parse_qsl(params)

		if len(params) > 0:
			args = {}
			for k, v in params:
				try:
					e = ast.literal_eval(v)
					args[k] = e
				except ValueError:
					args[k] = v
					pass
		else:
			args = params

		alog.debug("Parsed args: {}".format(args))

		result = ""
		for m in modules:
			function = getattr(m, method)
			if function:
				result = function(**args)
				break

		# We must return a string for the Flask view
		return str(result)

	return app



def signal_handler(signal, frame):
    print('Shutting down...')

    for m in modules:
		del(m)

	gc.collect()
    sys.exit(0)



if __name__ == "__main__":
	config = configparser.ConfigParser()
	config.read("config.ini")

	key = config['remu']['secret_key'].encode()
	f = fernet.Fernet(key)

	alog = configure_logger('default', 'log.txt')

	parser = argparse.ArgumentParser(description="Remote Emulation Sandbox")
	parser.add_argument("--iface", "-i", default="0.0.0.0", help="Interface the Flask application should run on.")
	parser.add_argument("--port", "-p", type=int, default=9000, help="Port the Flask application should run on.")
	parser.add_argument("--web", "-w", action="store_true", help="Run the web module.")
	parser.add_argument("--nginx", "-n", action="store_true", help="Run the NGINX module.")
	parser.add_argument("--manager", "-m", action="store_true", help="Run the Manager module.")
	parser.add_argument("--server", "-s", action="store_true", help="Run the Server module.")
	parser.add_argument("--import-workshops", action="store_true", help="Import workshop appliances.")
	args = parser.parse_args()

	# Use the arguments to determine which modules to run
	modules = []

	nginx = None	
	if args.nginx:
		from remu.nginx import Nginx
		nginx = Nginx()
		modules.append(nginx)

	server = None
	if args.server:
		from remu.server import Server
		server = Server()
		modules.append(server)

		if args.import_workshops:
			server.import_templates()

	manager = None
	if args.manager:
		from manager import Manager
		manager = Manager(server=server, nginx=nginx)
		modules.append(manager)

	# if args.web: 
	# 	from web.service import Website
	# 	modules.append(Website(manager=manager))

	# Create our flask application
	app = create_app()

	# Set our listener to handle SIGINT and terminate the service
	signal.signal(signal.SIGINT, signal_handler)

	# Start the service
	remu = wsgi.WSGIServer((args.iface, args.port), app)
	remu.serve_forever()