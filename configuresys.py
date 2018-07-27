import mongoengine

from remu.settings import config
from remu.models import User

# Create config.ini
print("Configuring the system")

remu_addr = raw_input("Enter the ip address for the REmuBox service (default: 0.0.0.0)")
if not remu_addr:
	remu_addr = '0.0.0.0'

remu_port = raw_input("Enter the associated port number (default: 56783)")
if not remu_port:
	remu_port = '56783'

nginx_addr = raw_input("Enter the ip address for NGINX (default: 127.0.0.1)")
if not nginx_addr:
	nginx_addr = '127.0.0.1'

nginx_port = raw_input("Enter the associated port number (default: 9000)")
if not nginx_port:
	nginx_port = '9000'


# We need to create a user for the administration
print("Configuring the account for the administration portion of the website")
username = raw_input("Enter a username: ")
password = raw_input("Enter a password: ")

try:
	mongoengine.connect('remubox')
	account = User(
		name=username,
		password=password
	)
	account.save()
except Exception:
	print("Unable to create user for administration!")

# Create the NGINX configuration file
conf = '/etc/nginx/nginx.conf'
template = './setup/nginx.conf'

with open(conf, 'w') as f:
    text = render_template(
    	template,
    	address=addr,
    	port=port,
    	static=static
    )
    f.write(text)


