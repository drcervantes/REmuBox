import zipfile
import os
import logging

from flask_login import login_required, current_user, login_user, logout_user
from flask import Blueprint, redirect, render_template, url_for, send_from_directory, current_app, session
from werkzeug.utils import secure_filename

import remu.forms as forms
import remu.database as db
from remu.settings import config


l = logging.getLogger('default')

user_bp = Blueprint("user", __name__)

@user_bp.route("/")
def index():
    workshops = db.get_all_workshops()
    for w in workshops:
        w['display_name'] = w['name'].replace("_", " ")

    sid = None
    if "sid" in session:
        # If the session has been recycled, clear the cookie
        if not db.session_exists(session["sid"]):
            session.pop("sid", None)

        # Otherwise we include the existing session id for reconnect
        else:
            sid = session["sid"]

    return render_template("index.html", workshops=workshops, sid=sid)

@user_bp.route('/checkout/<os_type>/<workshop>')
def checkout(os_type, workshop):
    # Get handle to manager module
    manager = current_app.config['MANAGER']

    ids = manager.start_workshop(workshop='Route_Hijacking')

    # Start_workshop returns a list so we take the first element, split
    # the name by '_' and take the first part (i.e. session_port)
    sid = ids[0].split("_")[0]

    # Store it in a cookie managed by Flask
    session["sid"] = sid

    # We need the address for nginx
    addr = "{}:{}".format(config["NGINX"]["address"], config["NGINX"]["port"])

    if os_type == "windows":
        template = "rdp.jnj2"
    elif os_type == "linux":
        template = "rdp.jnj2"
    else:
        return "Invalid platform choice."

    if len(ids) > 1:
        # We have multiple machines with VRDE ports so we want to combine
        # them into a zip file for the user
        base_dir = os.path.join(config["REMU"]["workshops"], workshop)
        machines = [name[:name.rfind("_")] for name in db.get_vrde_machine_names(sid)]

        # Create the rdp files to stash in the zip
        files = []
        for i, session_id in enumerate(ids):
            file = os.path.join(base_dir, machines[i])
            with open(file, 'w') as f:
                f.write(render_template(template, address=addr, session=session_id))
                files.append(file)

        # Zip them up
        zip_file = os.path.join(base_dir, sid)
        with zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for f in files:
                zipf.write(f)

        # Delete generated rdp files
        for f in files:
            os.remove(f)

        return zip_file

    return render_template(template, address=addr, session=ids[0])







"""
Admin interface
"""
admin_bp = Blueprint("admin", __name__)

@admin_bp.route('/')
@login_required
def home():
    return render_template('home.html')

@admin_bp.route('/static/<path:path>')
def assets(path):
    return send_from_directory('static', path)

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
    # Get the data to populate the web page here
    
    return render_template('servers.html')

@admin_bp.route('/add_server', methods=['GET', 'POST'])
@login_required
def add_server():
    form = forms.AddServerForm()
    if form.validate_on_submit():
        db.insert_server(form.address.data, form.port.data)
        return redirect(url_for('admin.home'))
    return render_template('add_server.html', form=form)

@admin_bp.route('/add_workshop', methods=['GET', 'POST'])
@login_required
def add_workshop():
    form = forms.AddWorkshopForm()
    if form.validate_on_submit():
        l.debug("docs: %s", str(form.documents.data))

        base_dir = os.path.join(config["REMU"]["workshops"], form.name.data, "documents")
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)

        files = []
        for doc in form.documents.data:
            secured_name = secure_filename(doc.filename)
            doc.save(os.path.join(base_dir, secured_name))
            files.append(secured_name)

        db.insert_workshop(
            form.name.data,
            form.description.data,
            form.mini.data,
            form.maxi.data,
            files,
            form.enabled.data
        )

        return redirect(url_for('admin.home'))
    return render_template('add_workshop.html', form=form)
