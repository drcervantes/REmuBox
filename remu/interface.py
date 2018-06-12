from flask_login import login_required, current_user, login_user, logout_user
from flask import Blueprint, redirect, render_template, url_for, current_app, send_from_directory
import remu.forms as forms
import remu.database as db

bp = Blueprint("gui", __name__)

@bp.route('/')
@login_required
def home():
    return render_template('home.html')

@bp.route('/static/<path:path>')
def assets(path):
    return send_from_directory('static', path)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('gui.home'))
    form = forms.LoginForm()
    if form.validate_on_submit():
        user = db.get_user(form.username.data)
        if user is None or not user.check_password(form.password.data):
            print('Invalid username or password')
            return redirect(url_for('gui.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('gui.home'))
    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('gui.login'))

@bp.route('/servers', methods=['GET', 'POST'])
@login_required
def servers():
    return render_template('servers.html')

@bp.route('/add_server', methods=['GET', 'POST'])
@login_required
def add_server():
    form = forms.AddServerForm()
    if form.validate_on_submit():
        db.insert_server(form.address.data, form.port.data)
        return redirect(url_for('gui.home'))
    return render_template('add_server.html', form=form)

@bp.route('/add_workshop', methods=['GET', 'POST'])
@login_required
def add_workshop():
    form = forms.AddWorkshopForm()
    if form.validate_on_submit():
        db.insert_workshop(
            form.name.data,
            form.description.data,
            form.mini.data,
            form.maxi.data,
            form.walkthrough.data,
            form.enab.data
        )
        # form.file.data.save('uploads/' + filename)
        return redirect(url_for('gui.home'))
    return render_template('add_workshop.html', form=form)
