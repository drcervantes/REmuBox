import logging
from logging.config import dictConfig
from flask import Flask, g

alog = util.configure_logger('default', 'log.txt')



'''
what i want to do here:
	need to load from config
	the config can have the remote properties for a module - if the module is specified
	as an argument to run the service locally then ignore the config

	if being run remotely then register them into a list for method calls
	it not then call the methods 


'''

def configure_logger(name, log_path):
	logging.config.dictConfig({
		'version': 1,
		'formatters': {
			'default': {'format': '%(asctime)s - %(levelname)s - %(message)s', 'datefmt': '%Y-%m-%d %H:%M:%S'}
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
				'filename': log_path,
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
	return logging.getLogger(name)

def create_app(config=None):
    app = Flask('remu')

    app.config.update(dict(
        DEBUG=True,
        SECRET_KEY=b'_5#y2L"F4Q8z\n\xec]/'
    ))
    app.config.update(config or {})

    app.register_blueprint()

    return app

def connect_db():
	with MongoClient('192.168.1.2',27017) as client:
		try:
			client.server_info()
		except ServerSelectionTimeoutError:
			logging.error("Unable to connect to database server.")
			sys.exit()
		logging.debug("Connected to database server.")

	db = getattr(client, db_name) 

