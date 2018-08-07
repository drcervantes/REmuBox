import ConfigParser
import mongoengine
import socket
import sys
import os
import jinja2
import subprocess
import io
import shutil

from cryptography.fernet import Fernet
from distutils.spawn import find_executable

from remu.models import User


def is_valid_ipv4_address(address):
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False

    return True

def sans_input(prompt, type_, default, min_=None, max_=None, ip=False):
    if min_ is not None and max_ is not None and max_ < min_:
        raise ValueError("min_ must be less than or equal to max_.")

    while True:
        ui = raw_input(prompt + " (default: {0}): ".format(default))

        if not bool(ui):
            return default

        try:
            ui = type_(ui)
        except ValueError:
            print("Input type must be {0}.".format(type_.__name__))
            continue
        
        if max_ and ui > max_:
            print("Input must be less than or equal to {0}.".format(max_))
            continue

        if min_ and ui < min_:
            print("Input must be greater than or equal to {0}.".format(min_))
            continue

        if ip and is_valid_ipv4_address(ui):
            return ui

        return ui

def render_jinja(template_loc, file_name, **context):
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_loc+'/')
    ).get_template(file_name).render(context)


try:
    config = ConfigParser.SafeConfigParser()
    config.read('config.ini')
except Exception:
    print('Unable to read config.ini file!')
    sys.exit()

print("Configuring REmuBox")

# Validation check (this could be better)
print("... validating config.ini")
if not is_valid_ipv4_address(config.get('REMU', 'address')):
    print('[REMU][address] is not a valid ip address!')
    sys.exit()

if not is_valid_ipv4_address(config.get('DATABASE', 'address')):
    print('[DATABASE][address] is not a valid ip address!')
    sys.exit()

if not is_valid_ipv4_address(config.get('MANAGER', 'address')):
    print('[MANAGER][address] is not a valid ip address!')
    sys.exit()

if not is_valid_ipv4_address(config.get('NGINX', 'address')):
    print('[NGINX][address] is not a valid ip address!')
    sys.exit()

port_range = range(1024, 65536)

if config.getint('REMU', 'port') not in port_range:
    print('[REMU][port] is not a valid port!')
    sys.exit()

if config.getint('DATABASE', 'port') not in port_range:
    print('[DATABASE][port] is not a valid port!')
    sys.exit()

if config.getint('MANAGER', 'port') not in port_range:
    print('[MANAGER][port] is not a valid port!')
    sys.exit()

if config.getint('NGINX', 'port') not in port_range:
    print('[NGINX][port] is not a valid port!')
    sys.exit()


# Generate new symmetric key
try:
    config.set('REMU', 'secret_key', Fernet.generate_key().decode())
    print('... symmetric key generated')
except Exception:
    print('... failed to create symmetric key!')


# Set paths
try:
    cwd = os.getcwd()
    config.set('REMU', 'log_file', os.path.join(cwd, 'log.txt'))
    config.set('REMU', 'workshops', os.path.join(cwd, 'remu', 'workshops'))
    print('... remubox paths set')
except Exception:
    print('... failed to set config paths!')


# Set location of VBoxManage
vmng = find_executable('VBoxManage')
if vmng:
    try:
        config.set('REMU', 'vbox_manage', vmng)
        print('... VBoxManage path set')
    except Exception:
        print('... failed to set VBoxManage path!')


# Create the mongoDB configuration file
if find_executable('mongod'):
    try:
        addr = config.get('DATABASE', 'address')
        port = config.get('DATABASE', 'port')
        verbose = config.get('DATABASE', 'verbose')

        with io.open('/etc/mongodb.conf', 'w', encoding='utf-8') as f:
            text = render_jinja(
                'setup',
                'mongodb.conf',
                bind_ip=addr,
                port=port,
                verbose=verbose
            )
            f.write(text)

        print("... wrote mongodb.conf file")
    except Exception:
        print('... failed to write mongodb.conf file!')

    try:
        subprocess.check_call(["systemctl", "restart", "mongod"])
        print('... mongodb service restarted')
    except subprocess.CalledProcessError:
        try:
            subprocess.check_call(["systemctl", "restart", "mongodb"])
            print('... mongodb service restarted')
        except subprocess.CalledProcessError:
            print('... failed to restart mongodb service!')


    # We need to create a user for the administration
    print("... configuring the account for the administration portion of the website")
    username = sans_input("    ... enter a username", str, "admin")
    password = sans_input("    ... enter a password", str, "admin")

    try:
        mongoengine.connect(
            'remubox',
            username=config.get('DATABASE', 'username'),
            password=config.get('DATABASE', 'password')
        )
        account = User(name=username, password=password)
        account.save()
    except Exception:
        print("... unable to create user for administration!")

# Create the NGINX configuration file
if find_executable('nginx'):
    with open('/etc/nginx/rdp_maps.conf', 'w'):
        print('... created empty rdp_maps.conf')
        pass

    with open('/etc/nginx/rdp_upstreams.conf', 'w'):
        print('... created empty rdp_upstreams.conf')
        pass

    try:
        src = os.path.join(os.getcwd(), 'setup', 'rdp_hook.js')
        dst = '/etc/nginx/rdp_hook.js'
        shutil.copyfile(src, dst)
        print("... copied rdp_hook.js to nginx root")
    except Exception:
        print("... failed to copy rdp_hook.js to nginx root!")

    try:
        addr = config.get('NGINX', 'address')
        port = config.get('NGINX', 'port')
        static = os.path.join(os.getcwd(), 'remu', 'workshops')

        with io.open('/etc/nginx/nginx.conf', 'w', encoding='utf-8') as f:
            text = render_jinja(
                'setup',
                'nginx.conf',
                address=addr,
                port=port,
                static=static
            )
            f.write(text)

        print("... wrote nginx.conf file")
    except Exception:
        print('... failed to write nginx.conf file!')

    try:
        subprocess.check_call(["systemctl", "restart", "nginx"])
        print('... nginx service restarted')
    except subprocess.CalledProcessError:
        print('... failed to restart nginx service!')

with open('config.ini', 'wb') as f:
    config.write(f)
    print('... configuration file rewritten')

print('Configuration complete!')