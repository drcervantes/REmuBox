import string
import random
import logging
from logging.config import dictConfig

def rand_str(length):
	return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(length))

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