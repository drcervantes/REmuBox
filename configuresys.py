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


# To add a new workshop:
# 	1. Create a new folder in the workshops directory with the name of your workshop.
# 	2. Move the .ova files for the workshop into the folder.
# 	3. Create a config.xml file in the same folder.
# 	4. Optional: move any materials into a folder called materials.

# 	Resulting directory structure should look similar to:
# 	workshops/
# 		My_Workshop/
# 			appliance.ova
# 			config.xml
# 			materials/
# 				walkthrough.doc

# 	5. Import the workshop into VirtualBox through REmuBox with the following command:
# 		python -m remu -s --import-workshops

# 	This process may take a while.

# 	6. Stop the service with Ctrl-C and start the website module with:
# 		python -m remu -nw

# 	7. Access the admin panel (default is http://127.0.0.1/admin).
# 	8. Navigate to workshops using the menu on the left.
# 	9. Click the Add a New Workshop button and fill out the form.
# 	10. Once finished, stop the service and restart with running all modules:
# 		python -m remu

# 	11. You should now see your workshop if you navigate to the user website (default is http://127.0.0.1).