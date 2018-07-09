""" TODO """
import logging
import time

from remu.models import Server, Workshop, Session, User, Machine
from remu.settings import config

l = logging.getLogger(config["REMU"]["logger"])

def session_exists(sid):
    for server in Server.objects():
        if sid in server.sessions:
            return True
    return False

def get_workshop(**kwargs):
    """Returns the workshop entry corresponding to the workshop name."""
    return Workshop.objects(**kwargs).first().to_mongo().to_dict()

def get_workshop_from_session(ip, sid):
    server = Server.objects(ip=ip).first()
    session = server.sessions[sid]
    return session.workshop.to_mongo().to_dict()

def get_server_from_session(sid):
    for server in Server.objects():
        if sid in server.sessions:
            return server.to_mongo().to_dict()
    return None

def get_vrde_machine_names(sid):
    server = get_server_from_session(sid)
    return [machine['name'] for machine in server['sessions'][sid]['machines'] if machine['port'] > 1]

def get_all_workshops():
    """Returns all workshop entries as a list of dictionaries unless json is True."""
    workshops = [w.to_mongo().to_dict() for w in Workshop.objects()]
    for w in workshops:
        w['_id'] = str(w['_id'])
    return workshops

def get_vrde_ports(sid):
    server = get_server_from_session(sid)
    return [machine['port'] for machine in server['sessions'][sid]['machines'] if machine['port'] > 1]

def get_user(username):
    """ TODO """
    return User.objects(name=username).first()

def get_server(ip):
    """Returns the server entry corresponding to the server ip."""
    server = Server.objects(ip=ip).first()
    return server.to_mongo().to_dict()

def get_all_servers():
    """Returns all server entries as a list of dictionaries unless json is True."""
    servers = Server.objects().exclude('id')
    return [s.to_mongo().to_dict() for s in servers]

def get_session(ip, sid):
    """ TODO """
    server = Server.objects(ip=ip).first()
    return server.sessions[sid].to_mongo().to_dict()

def get_available_session(ip, workshop):
    """
    Returns the first available session for the specified workshop.
    """
    server = Server.objects(ip=ip).first()

    if server.sessions:
        for s_id, session in server.sessions.items():
            if session['available'] and session.workshop['name'] == workshop:
                return s_id
    return None

def get_active_sessions():
    """
    Return a dictionary containing all active sessions.
    """
    active = {}
    for server in get_all_servers():
        for sid, session in server['sessions'].items():
            if not session['available']:
                active[sid] = session
    return active

def session_count(ip, check_available=False):
    """
    Returns the current number of sessions. If check_available is true,
    it will return the current available sessions only.
    """
    server = Server.objects(ip=ip).first()

    if not check_available:
        return len(server.sessions)

    count = 0
    for dummy, session in server.sessions.items():
        if session['available']:
            count += 1
    return count

def session_count_by_workshop(workshop, ip=None, available=False):
    """
    Returns the current number of sessions for the specified workshop.
    """
    count = 0
    servers = (Server.objects(ip=ip) if ip else Server.objects())

    for server in servers:
        if not available:
            for dummy, session in server.sessions.items():
                if session.workshop.name == workshop:
                    count += 1
        else:
            for s_id, session in server.sessions.items():
                if session.available and session.workshop.name == workshop:
                    count += 1

    return count

def session_to_workshop_count(available=False):
    counts = {}
    for w in Workshop.objects():
        counts[w.name] = session_count_by_workshop(w.name, available=available)
    return counts

def update_session(ip, session_id, available):
    """Update an existing session in a server document."""
    server = Server.objects(ip=ip).first()

    server.sessions[session_id]['available'] = available
    server.save()

def update_session_ports(ip, session_id, ports):
    """Update an existing session in a server document."""
    server = Server.objects(ip=ip).first()

    server.sessions[session_id]['ports'] = ports
    server.save()

def update_server(ip, **kwargs):
    server = Server.objects(ip=ip).first()
    for k, v in kwargs.items():
        server[k] = v
    server.save()

def update_machines(ip, session_id, data):
    server = Server.objects(ip=ip).first()
    machines = server.sessions[session_id].machines

    # We want to replace any hyphens in the dictionary keys
    # to underscores to match the model
    for m in data:
        for k in m:
            if '-' in k:
                m[k.replace('-', '_')] = m.pop(k)

    for i, m in enumerate(machines):
        for k, v in data[i].items():
            m[k] = v
    server.save()

def update_workshop(oid, **kwargs):
    workshop = Workshop.objects(id=oid).first()
    for k, v in kwargs.items():
        workshop[k] = v
    workshop.save()

def insert_server(ip, port):
    """Insert a new server document."""
    try:
        server = Server(ip=ip, port=port)
        server.save()
        return True
    except Exception as exc:
        l.exception(str(exc))
        return False

def insert_workshop(name, desc, min_units, max_units, enabled):
    """ TODO """
    workshop = Workshop(
        name=name,
        description=desc,
        min_instances=min_units,
        max_instances=max_units,
        enabled=enabled
    )
    workshop.save()

def insert_session(ip, sid, name, password):
    """ TODO """
    workshop = Workshop.objects(name=name).first()
    session = Session(
        workshop=workshop,
        password=password,
        available=True,
        start_time=time.time()
    )
    server = Server.objects(ip=ip).first()
    server.sessions[sid] = session
    server.save()

def insert_machine(ip, sid, name, port):
    server = Server.objects(ip=ip).first()
    session = server.sessions[sid]
    session.machines.append(Machine(name=name, port=port))
    session.save()

def remove_session(ip, session_id):
    """Remove a session for the corresponding server document."""
    server = Server.objects(ip=ip).first()
    del server.sessions[session_id]
    server.save()

def remove_workshop(oid):
    """ TODO """
    workshop = Workshop.objects(id=oid).first()
    workshop.delete()

def remove_server(ip):
    """ TODO """
    try:
        server = Server.objects(ip=ip).first()
        server.delete()
        return True
    except Exception:
        l.exception("Couldn't remove server entry")
        return False
