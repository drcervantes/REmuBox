from gevent import monkey
monkey.patch_all()
from gevent.pywsgi import WSGIServer

import logging
from logging.config import dictConfig
from flask import Flask, request
import argparse
from urllib.parse import urlparse, parse_qsl
from ast import literal_eval
import util



def create_app(config=None):
	app = Flask('remu')

	app.config.update(dict(
		DEBUG=True,
		SECRET_KEY=b'_5#y2L"F4Q8z\n\xec]/'
	))
	app.config.update(config or {})

	@app.route('/<path:path>')
	def catch_all(path):
		if "favicon.ico" in path:
			return ""
		
		f.decrypt(token)

		url = urlparse(request.url)
		alog.debug("Received URL: {}".format(url.path))
		method = url.path[1:]
		parsed = parse_qsl(url.query) # returns a list of tuples

		if len(parsed) > 0:
			args = {}
			for k, v in parsed:
				try:
					e = literal_eval(v)
					args[k] = e
				except ValueError:
					args[k] = v
					pass
		else:
			args = url.query

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


if __name__ == "__main__":
	key = b'ajkhUoSDyYDMGgARPrqdTR5JZRMz8S3YoNYgAwGkw8Q='
	f = Fernet(key)

	alog = util.configure_logger('default', 'log.txt')

	parser = argparse.ArgumentParser(description="Remote Emulation Sandbox")
	parser.add_argument("ip", help="Interface the Flask application should run on.", default="0.0.0.0")
	parser.add_argument("port", help="Port the Flask application should run on.", default=9000)
	parser.add_argument("--web", "-w", action="store_true", help="Run the web module.")
	parser.add_argument("--nginx", "-n", action="store_true", help="Run the NGINX module.")
	parser.add_argument("--manager", "-m", action="store_true", help="Run the Manager module.")
	parser.add_argument("--server", "-s", action="store_true", help="Run the Server module.")
	args = parser.parse_args()

	modules = []

	nginx = None	
	if args.nginx:
		from nginx import Nginx
		nginx = Nginx()
		modules.append(nginx)

	server = None
	# if args.server:
	# 	from server.service import Server
	# 	server = Server()
	# 	modules.append(server)

	manager = None
	if args.manager:
		from manager.manager import Manager
		manager = Manager(server=server, nginx=nginx)
		modules.append(manager)

	# if args.web: 
	# 	from web.service import Website
	# 	modules.append(Website(manager=manager))

	app = create_app()

	# Pretty sure I don't need this because all flask calls go through a single method
	# for m in reversed(modules):
	# 	app.register_blueprint(m.bp)
	# 	if isinstance(m, Website) or isinstance(m, Manager):
	# 		break

	server = WSGIServer(('0.0.0.0', 5000), app)
	server.serve_forever()