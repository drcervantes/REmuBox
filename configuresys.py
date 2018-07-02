import mongoengine

from remu.settings import config
from remu.models import User

# We need to create a user for the administration
try:
	mongoengine.connect('remubox')
	account = User(
		name=config['ADMIN']['username'],
		password=config['ADMIN']['password']
	)
	account.save()
except Exception:
	print("Unable to create user for administration!")
