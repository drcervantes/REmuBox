""" TODO """

# The primary purpose of the gevent.monkey module is to carefully patch, in place,
# portions of the standard library with gevent-friendly functions that behave in
# the same way as the original (at least as closely as possible).
import gevent.monkey
gevent.monkey.patch_all()

import gevent
import gevent.pywsgi as wsgi
import logging
import logging.config
import cryptography.fernet as fernet
import urllib.parse as ulib
import flask
import argparse
import ast
import signal
import sys
import flask_login
import remu.database as db
from remu.settings import config

def create_app(modules):
    """
    Setup the Flask application to handle any remote service routine calls. This includes
    interaction between the modules when run remotely and the front-end.
    """
    app = flask.Flask('remu')

    app.config.update(dict(
        DEBUG=True,
        SECRET_KEY=config['REMU']['secret_key'].encode()
    ))

    key = config['REMU']['secret_key'].encode()
    fern = fernet.Fernet(key)

    login_manager = flask_login.LoginManager(app)
    login_manager.login_view = 'gui.login'
    login_manager.user_loader(db.get_user)

    @app.route('/')
    def catch_root():
        return "portal"

    @app.route('/<path:path>')
    def catch_all(path):
        """ TODO """
        if "favicon.ico" in path:
            return ""

        url = ulib.urlparse(flask.request.url)
        path = url.path[1:].encode()
        path = fern.decrypt(path).decode()

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

def main():
    """ TODO """
    args = parse_arguments()

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

    if args.manager or args.web:
        import mongoengine
        mongoengine.connect(
            config['DATABASE']['name'],
            host=config['DATABASE']['ip'], 
            port=int(config['DATABASE']['port']))

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

        # if args.import_workshops:
        #     server.import_templates()

    manager = None
    if args.manager:
        from remu.manager import Manager
        manager = Manager(config, server, nginx)
        modules.append(manager)


    def signal_handler(sig, frame):
        """ TODO """
        print('Shutting down...')
        # remu.stop()
        for module in modules:
            del module

        sys.exit(0)

    # Create our flask application
    # app = create_app(config, modules)

    # if args.web:
    #     from remu.interface import bp
    #     app.register_blueprint(bp, url_prefix='/admin')

    # Set our listener to handle SIGINT and terminate the service
    signal.signal(signal.SIGINT, signal_handler)

    # # Start the service
    # service = wsgi.WSGIServer((config['REMU']['interface'], int(config['REMU']['port'])), app)
    # service.serve_forever()


LOG = logging.getLogger('default')
main()
