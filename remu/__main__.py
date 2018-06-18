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
import flask_login

import remu.database as db
from remu.settings import config

def create_app():
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

        l.debug("Received path: %s", url.path)

        method, query = path.split('?')
        query = ulib.parse_qsl(query)

        if query:
            params = {}
            for k, v in query:
                try:
                    e = ast.literal_eval(v)
                    args[k] = e
                except ValueError:
                    args[k] = v
        else:
            params = query

        l.debug("Parsed args: %s", str(params))

        result = ""
        for m in modules:
            function = getattr(m, method)
            if function:
                result = function(**params)
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

l = logging.getLogger('default')

if args.manager or args.web:
    import mongoengine
    mongoengine.connect(
        config['DATABASE']['name'],
        host=config['DATABASE']['ip'],
        port=int(config['DATABASE']['port'])
    )

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
        from remu.importer import Templates
        with Templates() as t:
            t.import_new()

manager = None
if args.manager:
    from remu.manager import Manager
    manager = Manager(server, nginx)
    modules.append(manager)

# Create our flask application
application = create_app()

if args.web:
    from remu.interface import bp
    application.register_blueprint(bp, url_prefix='/admin')

try:
    l.info("Starting service. Use Ctrl-C to terminate gracefully.")
    service = wsgi.WSGIServer((config['REMU']['interface'], int(config['REMU']['port'])), application)
    service.serve_forever()
except (KeyboardInterrupt, SystemExit):
    l.info('Shutting down...')

    if service.started:
        service.close()

    for module in modules:
        del module
