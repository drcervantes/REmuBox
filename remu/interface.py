import zipfile
import os
import logging
import time

from flask_login import login_required, current_user, login_user, logout_user
from flask import (Blueprint, redirect, render_template, url_for, send_from_directory, 
    current_app, session, request, send_file, flash)
from werkzeug.utils import secure_filename

try:
    from os import scandir
except ImportError:
    from scandir import scandir  # use scandir PyPI module on Python < 3.5

import remu.forms as forms
import remu.database as db
from remu.settings import config


l = logging.getLogger(config["REMU"]["logger"])

user_bp = Blueprint("user", __name__)
admin_bp = Blueprint("admin", __name__)


@user_bp.route("/")
def index():
    # Get enabled workshops
    workshops = [w for w in db.get_all_workshops() if w['enabled']]

    for w in workshops:
        if not bool(w['display']):
            w['display'] = w['name'].replace("_", " ")

        materials = os.path.join(config["REMU"]["workshops"], w['name'], "materials")
        if os.path.exists(materials):
            w['materials'] = [doc.name for doc in scandir(materials) if doc.is_file()]
        else:
            w['materials'] = None

    sid = None
    if "sid" in session:
        # Start_workshop returns a list so we take the first element, split
        # the name by '_' and take the first part (i.e. session_port)
        sid = ids[0].split("_")[0]

        if not db.session_exists(sid):
            # If the session has been recycled, clear the cookie
            session.pop("sid", None)

    return render_template("index.html", workshops=workshops, sid=sid)


def build_rdp_files(ids, os_type):
    # We need the address for nginx
    addr = "{}:{}".format(config["NGINX"]["address"], config["NGINX"]["port"])

    if os_type == "windows":
        template = "rdp.jnj2"
    elif os_type == "linux":
        template = "rdp.jnj2"
    else:
        raise Exception

    if len(ids) > 1:
        # We have multiple machines with VRDE ports so we want to combine
        # them into a zip file for the user

        mem_zip = io.BytesIO()

        with zipfile.ZipFile(mem_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for sid, machine_name in zip(ids, machines):
                filename = machine_name + '.rdp'

                mem_file = io.StringIO(filename)
                mem_file.write(render_template('rdp.jnj2', address=addr, session=sid))

                zf.writestr(filename, mem_file.getvalue())

                mem_file.close()

        mem_zip.seek(0)

        zip_name = workshop + '.zip'
        return (zip_name, mem_zip)

    filename = workshop + '.rdp'
    mem_file = io.StringIO(filename)
    mem_file.write(render_template('rdp.jnj2', address=addr, session=ids[0]))
    mem_file.seek(0)

    return (filename, mem_file)


@user_bp.route('/checkout/<path:os_type>/<path:workshop>')
def checkout(os_type, workshop):
    # Prevent repeated requests
    if "sid" in session:
        flash("You've already started a workshop! Try the reconnect button or wait for your session to be recycled.")
        return redirect(url_for('user.index'))

    # Get handle to manager module
    manager = current_app.config['MANAGER']

    ids = manager.start_workshop(workshop=workshop)

    if not ids:
        l.error("Something weird happened. No IDs provided for checkout")
        flash("Error starting workshop! Please contact the adminstrator.")
        return redirect(url_for('user.index'))

    # Store ids in a cookie managed by Flask
    session["sid"] = ids

    try:
        name, file = build_rdp_files(ids, os_type)
        return send_file(file, attachment_filename=name, as_attachment=True)

    except Exception:
        l.exception("Invalid os type in RDP file creation!")
        flash("Invalid OS type!")
        return redirect(url_for('user.index'))


@user_bp.route('/materials/<path:workshop>/<path:filename>')
def fetch_document(workshop, filename):
    materials = os.path.join(config["REMU"]["workshops"], workshop, "materials")
    return send_from_directory(materials, filename, as_attachment=True)


@user_bp.route('/reconnect/<path:workshop>')
def reconnect(workshop):
    if "sid" not in session:
        flash("No session ID found!")
        return redirect(url_for('user.index'))

    ids = session["sid"]
    name, file = build_rdp_files(ids, os_type)

    return send_file(file, attachment_filename=name, as_attachment=True)


"""
Admin interface
"""

@admin_bp.route('/')
@login_required
def home():
    # Not the most optimal but we should clean up the data a bit for display
    data = db.get_all_servers()
    for server in data:
        for sid, s in server['sessions'].items():
            # Get workshop name by object id
            workshop = db.get_workshop(id=str(s["workshop"]))
            s["workshop"] = workshop["name"].replace("_", " ")

            # Get the length of time the session has been active
            hours, rem = divmod(time.time() - s["start_time"], 3600)
            minutes, seconds = divmod(rem, 60)
            s["time"] = "{:0>2}:{:0>2}:{:0>2}".format(int(hours), int(minutes), int(seconds))

            for machine in s['machines']:
                machine['name'] = machine['name'][:machine['name'].rfind('_')]
                machine['port'] = ("-" if machine['port'] == 1 else machine['port'])

    return render_template('home.html', server_data=data, counts=db.session_to_workshop_count())

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.home'))
    form = forms.LoginForm()
    if form.validate_on_submit():
        user = db.get_user(form.username.data)
        if user is None or not user.check_password(form.password.data):
            print('Invalid username or password')
            return redirect(url_for('admin.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('admin.home'))
    return render_template('login.html', form=form)

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))

@admin_bp.route('/servers', methods=['GET', 'POST'])
@login_required
def servers():
    return render_template('servers.html', server_data=db.get_all_servers())

@admin_bp.route('/servers/add', methods=['GET', 'POST'])
@login_required
def add_server():
    form = forms.AddServerForm()
    if form.validate_on_submit():
        db.insert_server(form.address.data, form.port.data)
        return redirect(url_for('admin.servers'))
    return render_template('add_server.html', form=form)

@admin_bp.route('/servers/edit/<path:address>', methods=['GET', 'POST'])
@login_required
def edit_server(address):
    form = forms.AddServerForm()
    if form.validate_on_submit():
        db.update_server(ip=form.address.data, port=form.port.data)
        return redirect(url_for('admin.servers'))

    server = db.get_server(address)
    form.address.data = address
    form.port.data = server['port']
    return render_template('add_server.html', form=form)

@admin_bp.route('/servers/remove/<path:address>', methods=['GET', 'POST'])
@login_required
def remove_server(address):
    db.remove_server(address)
    return redirect(url_for('admin.servers'))

@admin_bp.route('/workshops', methods=['GET', 'POST'])
@login_required
def workshops():
    return render_template('workshops.html', data=db.get_all_workshops())

@admin_bp.route('/workshops/add', methods=['GET', 'POST'])
@login_required
def add_workshop():
    form = forms.AddWorkshopForm()
    if form.validate_on_submit():
        # Check if workshop already exists
        if db.get_workshop(name=form.name.data):
            l.error("A workshop already exists under the name %s", form.name.data)
            flash("A workshop already exists by that name!")
            return render_template('add_workshop.html', form=form)

        # Create workshop folder if it doesn't exist
        _dir = os.path.join(config["REMU"]["workshops"], form.name.data)
        if not os.path.exists(_dir):
            l.debug("No workshop folder found. Creating: %s", _dir)
            os.mkdir(_dir)

        # Create materials folder if doesnt exist
        _dir = os.path.join(config["REMU"]["workshops"], form.name.data)
        if not os.path.exists(_dir):
            l.debug("No workshop folder found. Creating: %s", _dir)
            os.mkdir(_dir)

        # Save workshop material if any is provided
        # We check the first element because no input evaluates to ['']
        if bool(form.materials.data[0]):
            for doc in form.materials.data:
                secured_name = secure_filename(doc.filename)
                doc.save(os.path.join(base_dir, secured_name))

        db.insert_workshop(
            form.name.data,
            form.display.data,
            form.description.data,
            form.mini.data,
            form.maxi.data,
            form.enabled.data
        )

        return redirect(url_for('admin.workshops'))
    return render_template('add_workshop.html', form=form)

@admin_bp.route('/workshops/edit/<path:oid>', methods=['GET', 'POST'])
@login_required
def edit_workshop(oid):
    form = forms.AddWorkshopForm()
    if form.validate_on_submit():
        db.update_workshop(
            oid,
            name=form.name.data,
            description=form.description.data,
            min_instances=form.mini.data,
            max_instances=form.maxi.data,
            enabled=form.enabled.data
        )
        
        if bool(form.materials.data[0]):
            base_dir = os.path.join(config["REMU"]["workshops"], form.name.data, "materials")
            if not os.path.exists(base_dir):
                os.mkdir(base_dir)

            for doc in form.materials.data:
                secured_name = secure_filename(doc.filename)
                doc.save(os.path.join(base_dir, secured_name))

        return redirect(url_for('admin.workshops'))
    else:
        workshop = db.get_workshop(id=oid)
        form.name.data = workshop["name"]
        form.description.data = workshop["description"]
        form.mini.data = workshop["min_instances"]
        form.maxi.data = workshop["max_instances"]
        form.enabled.data = workshop["enabled"]

        materials = os.path.join(config["REMU"]["workshops"], workshop['name'], "materials")
        if os.path.exists(materials):
            mats = [doc.name for doc in scandir(materials) if doc.is_file()]
        else:
            mats = None

    return render_template('edit_workshop.html', form=form, materials=mats, oid=oid)

@admin_bp.route('/workshops/edit/<path:oid>/<path:material>', methods=['GET', 'POST'])
@login_required
def remove_material(oid, material):
    workshop = db.get_workshop(id=oid)
    file = os.path.join(config["REMU"]["workshops"], workshop["name"], "materials", material)

    try:
        os.remove(file)
    except os.error:
        l.exception("Unable to remove workshop (%s) material: %s", workshop["name"], file)

    return redirect(url_for('admin.edit_workshop', oid=oid))

@admin_bp.route('/workshops/remove/<path:oid>', methods=['GET', 'POST'])
@login_required
def remove_workshop(oid):
    db.remove_workshop(oid)
    return redirect(url_for('admin.workshops'))

@admin_bp.route('/kill_session/<path:sid>', methods=['GET', 'POST'])
@login_required
def kill_session(sid):
    manager = current_app.config['MANAGER']
    manager.stop_workshop(sid)
    return redirect(url_for('admin.home'))