from models import *
from bson import ObjectId

'''
	currently: 
		start_unit -> machine_name, port
	modify to:
		start_unit -> port
	machines can be killed by the ip and port number

'''



def get_all_workshops(name=None, json=False):
	""" Returns all workshop entries as a list of dictionaries unless json is True. """
	workshops = Workshop.objects.exclude('id')

	if json:
		return workshops.to_json()

	return [w.to_mongo().to_dict() for w in workshops]


def get_workshop_by_name(name, json=False):
	""" Returns the workshop entry corresponding to the workshop name. """
	workshops = Workshop.objects(name=name).exclude('id')

	if json:
		return workshops[0].to_json()

	return workshops[0].to_mongo().to_dict()


def get_server(ip, json=False):
	""" Returns the server entry corresponding to the server ip. """
	server = Server.objects(ip=ip).first()

	if json:
		return server.to_json()

	return server.to_mongo().to_dict()


def session_count(ip, name=None, check_available=False):
	""" Returns the current number of sessions. If check_available is true,
	it will return the current available sessions only. """
	server = get_server(ip)

	if not check_available:
		return len(server.sessions)

	count = 0
	for s_id, session in server.sessions.items():
		if session['available']:
			count += 1
	return count
	

def session_count_by_workshop(ip, name, check_available=False):
	""" Returns the current number of sessions for the specified workshop. """
	server = get_server(ip)
	count = 0

	if not check_available:
		for s_id, session in server.sessions.items():
			if session.workshop.name == name:
				count += 1
		return count

	for s_id, session in server.sessions.items():
		if session['available'] and session.workshop.name == name:
			count += 1
	return count


def insert_workshop(name, description, enabled, vpn_enabled, vpn_port, min_instances, max_instances):
	workshop = Workshop(name=name, description=description, enabled=enabled, vpn_enabled=vpn_enabled, vpn_port=vpn_port, 
		min_instances=min_instances, max_instances=max_instances)
	workshop.save()


def insert_session(server, workshop_name, ports, password, available):
	workshop = Workshop.objects(name=workshop_name).first()
	session = Session(workshop=workshop, ports=ports, password=password, available=available)
	session_id = str(ObjectId())
	server.sessions[session_id] = session
	server.save()
	return session_id

def remove_session(server, session_id):
	""" Remove a session for the corresponding server document. """
	del(server.sessions[session_id])
	server.save()

def update_session(server, session_id, available):
	""" Update an existing session in a server document. """
	server.sessions[session_id].available = available
	server.save()

def insert_server(ip):
	""" Insert a new server document. """
	server = Server(ip=ip)
	server.save()


connect('test')

# loc = Server(ip='127.0.0.1')
# loc.save()

# w = Workshop(name='route', description='hijacking', enabled=True, vpn_enabled=False, vpn_port=0, min_instances=0, max_instances=3)
# w.save()

# for i in range(0,3):
# 	insert_session(loc, 'route', [5001,5002,5003], 'datpass', True)


