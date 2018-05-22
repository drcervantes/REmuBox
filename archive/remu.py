""" TODO """

# The primary purpose of the gevent.monkey module is to carefully patch, in place,
# portions of the standard library with gevent-friendly functions that behave in
# the same way as the original (at least as closely as possible).
from gevent import monkey
monkey.patch_all()

import gevent
import logging
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

import remu.util


def create_app(config, modules):
    """
    Setup the Flask application to handle any remote service routine calls. This includes
    interaction between the modules when run remotely and the front-end.
    """
    app = flask.Flask('remu')

    app.config.update(dict(
        DEBUG=True,
        SECRET_KEY=config['REMU']['secret_key'].encode()
    ))

    @app.route('/<path:path>')
    def catch_all(path):
        """ TODO """
        if "favicon.ico" in path:
            return ""

        url = ulib.urlparse(flask.request.url)
        path = url.path[1:].encode()
        path = config['REMU']['fernet'].decrypt(path).decode()

        LOG.debug("Received path: %s", url.path)

        method, params = path.split('?')
        params = ulib.parse_qsl(params)

        if params:
            args = {}
            for k, v in params:
                try:
                    e = ast.literal_eval(v)
                    args[k] = e
                except ValueError:
                    args[k] = v
        else:
            args = params

        LOG.debug("Parsed args: %s", str(args))

        result = ""
        for module in modules:
            function = getattr(module, method)
            if function:
                result = function(**args)
                break

        # We must return a string for the Flask view --- needs to be encrypted??
        return str(result)

    return app

def parse_arguments():
    """ TODO """
    parser = argparse.ArgumentParser(description="Remote Emulation Sandbox")
    parser.add_argument(
        "--config",
        "-c",
        default="config.ini",
        help="Specify an alternative configuration file to use."
    )
    parser.add_argument(
        "--web",
        "-w",
        action="store_true",
        help="Run the web module."
    )
    parser.add_argument(
        "--nginx",
        "-n",
        action="store_true",
        help="Run the NGINX module."
    )
    parser.add_argument(
        "--manager",
        "-m",
        action="store_true",
        help="Run the Manager module."
    )
    parser.add_argument(
        "--server",
        "-s",
        action="store_true",
        help="Run the Server module."
    )
    parser.add_argument(
        "--import-workshops",
        action="store_true",
        help="Import workshop appliances."
    )
    return parser.parse_args()

def parse_config(path):
    """ TODO """
    parser = configparser.ConfigParser()
    parser.read(path)
    return {s:dict(parser.items(s)) for s in parser.sections()}

def main():
    """ TODO """
    args = parse_arguments()
    config = parse_config(args.config)

    key = config['REMU']['secret_key'].encode()
    config['REMU']['fernet'] = fernet.Fernet(key)

    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': config['REMU']['log_file'],
                'maxBytes': 1024
            }
        },
        'loggers': {
            'default': {
                'level': 'DEBUG',
                'handlers': ['console', 'file']
            }
        },
        'disable_existing_loggers': False
    })

    # Use the arguments to determine which modules to run
    modules = []

    nginx = None
    if args.nginx:
        from remu.nginx import Nginx
        nginx = Nginx(config)
        modules.append(nginx)

    server = None
    if args.server:
        from remu.server import Server
        server = Server(config)
        modules.append(server)

        if args.import_workshops:
            server.import_templates()

    manager = None
    if args.manager:
        from remu.manager import Manager
        manager = Manager(config=config, server=server, nginx=nginx)
        modules.append(manager)

    # if args.web:
    #   from web.service import Website
    #   modules.append(Website(manager=manager))

    def signal_handler(sig, frame):
        """ TODO """
        print('Shutting down...')
        # remu.stop()
        for module in modules:
            del module

        gc.collect()
        sys.exit(0)

    # Create our flask application
    app = create_app(config, modules)

    # Set our listener to handle SIGINT and terminate the service
    signal.signal(signal.SIGINT, signal_handler)

    # Start the service
    service = wsgi.WSGIServer((config['REMU']['interface'], config['REMU']['port']), app)
    service.serve_forever()

if __name__ == "__main__":
    LOG = logging.getLogger('default')
    main()
