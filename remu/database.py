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
    Returns the current number of available or unavailable sessions 
    for the specified workshop.  If no server is specified, then
    all servers will be counted.
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
    """
    Obtain a dictionary mapping workshop names to the amount of available
    or unavailable sessions for each workshop.
    """
    counts = {}

    for w in Workshop.objects():
        counts[w.name] = session_count_by_workshop(w.name, available=available)

    return counts


def update_session(ip, sid, available):
    """
    Update an existing session in a server document.
    """

    if not ip:
        l.error("Cannot update server with no ip address!")
        raise Exception

    if not sid:
        l.error("A session must have an id!")
        raise Exception

    try:
        server = Server.objects(ip=ip).first()

        server.sessions[sid]['available'] = available
        server.save()

    except Exception:
        l.exception("Failed to update session %s", sid)
        raise


def update_server(ip, **kwargs):
    """
    Update a server document.
    """

    if not ip:
        l.error("Cannot update server with no ip address!")
        raise Exception

    try:
        server = Server.objects(ip=ip).first()

        for k, v in kwargs.items():
            server[k] = v

        server.save()

    except Exception:
        l.exception("Failed to update server %s", ip)
        raise


def update_machines(ip, sid, data):
    """
    Update a machine document embedded in a session document.
    data - list of dictionaries
    """

    if not ip:
        l.error("Cannot update machines with no ip address!")
        raise Exception

    if not sid:
        l.error("A session must have an id!")
        raise Exception

    try:
        server = Server.objects(ip=ip).first()
        machines = server.sessions[sid].machines

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

    except Exception:
        l.exception("Failed to update machines for %s", sid)
        raise


def update_workshop(oid, **kwargs):
    """
    Update a workshop document.
    """

    if not oid:
        l.error("Cannot update workshop without id!")
        raise Exception

    try:
        workshop = Workshop.objects(id=oid).first()
        for k, v in kwargs.items():
            workshop[k] = v
        workshop.save()

    except Exception:
        l.exception("Failed to update workshop (%s)", oid)
        raise


def insert_server(ip, port):
    """
    Insert a new server document.
    """

    if not ip:
        l.error("Cannot insert server with no ip address!")
        raise Exception

    try:
        server = Server(ip=ip, port=port)
        server.save()

    except Exception:
        l.exception("Failed inserting server %s:%d", ip, port)
        raise


def insert_workshop(name, desc, min_units, max_units, enabled):
    """
    Insert a new workshop document.
    """
    if not name:
        l.error("Cannot insert workshop with no name!")
        raise Exception

    try:
        workshop = Workshop(
            name=name,
            description=desc,
            min_instances=min_units,
            max_instances=max_units,
            enabled=enabled
        )
        workshop.save()

    except Exception:
        l.exception("Failed inserting workshop %s", name)
        raise


def insert_session(ip, sid, name, password):
    """
    Embed a new session document into the server document.
    """

    if not sid:
        l.error("A session must have an id!")
        raise Exception

    if not password:
        l.error("A session cannot have a blank password!")
        raise Exception

    try:
        workshop = Workshop.objects(name=name).first()
        session = Session(
            workshop=workshop,
            password=password,
            available=True,
            start_time=time.time()
        )
        server = Server.objects(ip=ip).first()

        if sid in server.sessions:
            l.error("Cannot insert session with duplicate id!")
            raise Exception

        server.sessions[sid] = session
        server.save()

    except Exception:
        l.exception("Failed inserting session %s", sid)
        raise


def insert_machine(ip, sid, name, port):
    """
    Embed a new machine into the embedded session document.
    """

    if not name:
        l.error("A machine has no name!")
        raise Exception

    try:
        server = Server.objects(ip=ip).first()
        session = server.sessions[sid]
        session.machines.append(Machine(name=name, port=port))
        session.save()

    except Exception:
        l.exception("Failed to insert machine %s into %s", name, sid)
        raise


def remove_session(ip, sid):
    """
    Remove a session for the corresponding server document.
    """

    if not ip:
        l.error("Cannot remove session without ip!")
        raise Exception

    if not sid:
        l.error("Cannot remove session without id!")
        raise Exception

    try:
        server = Server.objects(ip=ip).first()
        del server.sessions[sid]
        server.save()

    except Exception:
        l.exception("Failed to remove session %s", sid)
        raise


def remove_workshop(oid):
    """
    Remove a workshop document.
    """

    if not oid:
        l.error("Cannot remove workshop without id!")
        raise Exception

    try:
        workshop = Workshop.objects(id=oid).first()
        workshop.delete()

    except Exception:
        l.exception("Failed to remove workshop %s", oid)
        raise


def remove_server(ip):
    """
    Remove a server document.
    """

    if not ip:
        l.error("Cannot remove server without ip!")
        raise Exception

    try:
        server = Server.objects(ip=ip).first()
        server.delete()

    except Exception:
        l.exception("Failed to remove server %s", ip)
        raise
