""" TODO """
import mongoengine
from remu.models import Server, Workshop, Session, User

def get_workshop(name, json=False):
    """Returns the workshop entry corresponding to the workshop name."""
    workshop = Workshop.objects(name=name).first()

    if json:
        return workshop.to_json()

    return workshop.to_mongo().to_dict()

def get_all_workshops(json=False):
    """Returns all workshop entries as a list of dictionaries unless json is True."""
    workshops = Workshop.objects().exclude('id')

    if json:
        return workshops.to_json()

    return [w.to_mongo().to_dict() for w in workshops]

def get_user(username):
    return User.objects(name=username).first()

def get_server(host, json=False):
    """Returns the server entry corresponding to the server host."""
    server = Server.objects(ip=host).first()

    if json:
        return server.to_json()

    return server.to_mongo().to_dict()

def get_all_servers(json=False):
    """Returns all server entries as a list of dictionaries unless json is True."""
    servers = Server.objects().exclude('id')

    if json:
        return servers.to_json()

    return [s.to_mongo().to_dict() for s in servers]

def get_session(host, session_id):
    """ TODO """
    server = Server.objects(ip=host).first()
    return server.session[session_id].to_mongo().to_dict()

def get_available_session(host, workshop):
    """Returns the first available session for the specified workshop."""
    server = Server.objects(ip=host).first()

    for s_id, session in server.sessions.items():
        if session['available'] and session.workshop['name'] == workshop:
            return s_id, session['password']
    return None

def session_count(host, check_available=False):
    """Returns the current number of sessions. If check_available is true,
    it will return the current available sessions only."""
    server = Server.objects(ip=host).first()

    if not check_available:
        return len(server.sessions)

    count = 0
    for dummy, session in server.sessions.items():
        if session['available']:
            count += 1
    return count

def session_count_by_workshop(host, name, check_available=False):
    """Returns the current number of sessions for the specified workshop."""
    server = Server.objects(ip=host).first()
    count = 0

    if not check_available:
        for dummy, session in server.sessions.items():
            if session.workshop.name == name:
                count += 1
        return count

    for s_id, session in server.sessions.items():
        if session['available'] and session.workshop['name'] == name:
            count += 1
    return count

def update_session(host, session_id, available):
    """Update an existing session in a server document."""
    server = Server.objects(ip=host).first()

    server.sessions[session_id]['available'] = available
    server.save()

def update_session_ports(host, session_id, ports):
    """Update an existing session in a server document."""
    server = Server.objects(ip=host).first()

    server.sessions[session_id]['ports'] = ports
    server.save()

def insert_server(host, port):
    """Insert a new server document."""
    try:
        server = Server(ip=host, port=port)
        server.save()
        return True
    except Exception as exc:
        # log.exception(str(e))
        return False

def insert_workshop(name, desc, enabled, vpn_enabled, vpn_port, min_units, max_units):
    """ TODO """
    workshop = Workshop(
        name=name,
        description=desc,
        enabled=enabled,
        vpn_enabled=vpn_enabled,
        vpn_port=vpn_port,
        min_instances=min_units,
        max_instances=max_units
    )
    workshop.save()

def insert_session(session_id, host, workshop_name, ports, password, available):
    """ TODO """
    workshop = Workshop.objects(name=workshop_name).first()
    session = Session(workshop=workshop, ports=ports, password=password, available=available)
    server = Server.objects(ip=host).first()
    server.sessions[session_id] = session
    server.save()
    return session_id

def remove_session(host, session_id):
    """Remove a session for the corresponding server document."""
    server = Server.objects(ip=host).first()
    del server.sessions[session_id]
    server.save()

def remove_server(host):
    """ TODO """
    try:
        server = Server.objects(ip=host).first()
        server.delete()
        return True
    except Exception as exc:
        # log.exception(str(e))
        return False
