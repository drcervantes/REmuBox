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
from remu.nginx import Nginx
from remu.manager import Manager
from remu.server import WorkshopManager, PerformanceMonitor
from remu.remote import RemoteComponent
from remu.importer import Templates
from remu.interface import user_bp, admin_bp
from remu.settings import config

def create_app():
    """
    Setup the Flask application to handle any remote service routine calls. This includes
    interaction between the modules when run remotely and the front-end.
    """
    app = flask.Flask(__name__)

    app.config.update(dict(
        DEBUG=True,
        SECRET_KEY=config['REMU']['secret_key'].encode()
    ))

    key = config['REMU']['secret_key'].encode()
    fern = fernet.Fernet(key)

    # We are required to set user_loader to the method responsible for
    # user account lookup.
    login_manager = flask_login.LoginManager(app)
    login_manager.login_view = 'admin.login'
    login_manager.user_loader(db.get_user)

    # Ensure the application is able to reach the Manager module.
    for m in modules:
        if isinstance(m, Manager):
            app.config['MANAGER'] = m

    if "MANAGER" not in app.config:
        app.config['MANAGER'] = RemoteComponent(config['MANAGER']['address'], config['MANAGER']['port'], Manager)

    @app.route('/<path:path>')
    def catch_all(path):
        """ TODO """
        if "favicon.ico" in path:
            return ""

        url = ulib.urlparse(flask.request.url)
        path = url.path[1:].encode()
        path = fern.decrypt(path).decode()

        l.debug("Received path: %s", url.path)

        if path.find('?') > 0:
            method, query = path.split('?')
            query = ulib.parse_qsl(query)

            params = {}
            for k, v in query:
                try:
                    e = ast.literal_eval(v)
                    params[k] = e
                except ValueError:
                    params[k] = v
        else:
            method = path
            params = None

        l.debug("Parsed args: %s", str(params))

        result = ""
        for m in modules:
            try:
                function = getattr(m, method)
                if function:
                    result = function(**params) if params is not None else function()
                    break
            except AttributeError:
                pass

        # We must return a string for the Flask view --- needs to be encrypted??
        l.debug("Result: %s", str(result))
        return str(result)

    @app.before_request
    def assets():
        """
        Ugly workaround to deal with the inline resource requests from bundle.js
        """
        if "static" in flask.request.path:
            file = flask.request.path[flask.request.path.find("static")+7:]
            return flask.send_from_directory('static', file)
        return None

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
        host=config['DATABASE']['address'],
        port=int(config['DATABASE']['port'])
    )

# Use the arguments to determine which modules to run
modules = []

nginx = None
if args.nginx: 
    nginx = Nginx()
    modules.append(nginx)

server = None
monitor = None
if args.server:
    server = WorkshopManager()
    modules.append(server)

    monitor = PerformanceMonitor()
    modules.append(monitor)

    if args.import_workshops:
        with Templates() as t:
            t.import_new()

manager = None
if args.manager:
    # If NGINX is not running locally, create object to handle remote calls
    if not args.nginx:
        nginx = RemoteComponent(config['NGINX']['address'], config['NGINX']['port'], Nginx)

    manager = Manager(server, nginx, monitor)
    modules.append(manager)


# Create our flask application
application = create_app()

if args.web:
    application.register_blueprint(user_bp)
    application.register_blueprint(admin_bp, url_prefix='/admin')

try:
    l.info("+--------------------------------------------------+")
    l.info("Service running. Use Ctrl-C to terminate gracefully.")
    l.info("+--------------------------------------------------+")
    service = wsgi.WSGIServer((config['REMU']['interface'], int(config['REMU']['port'])), application)
    service.serve_forever()
except (KeyboardInterrupt, SystemExit):
    l.info('Shutting down...')

    if service.started:
        service.close()

    for module in modules:
        module.clean_up()
