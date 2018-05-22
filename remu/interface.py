from flask_login import login_required, current_user, login_user, logout_user
from flask import Blueprint, redirect, render_template, url_for, current_app
import remu.forms as forms
import remu.database as db

bp = Blueprint("gui", __name__)

@bp.route('/')
@login_required
def home():
    return render_template('home.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    app = current_app._get_current_object()
    app.login_manager.user_loader(db.get_user)

    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = forms.LoginForm()
    if form.validate_on_submit():
        user = db.get_user(form.username.data)
        if user is None or not user.check_password(form.password.data):
            print('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=True)
        return redirect(url_for('home'))
    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@bp.route('/servers', methods=['GET', 'POST'])
@login_required
def servers():
    form = forms.AddServerForm()
    if form.validate_on_submit():
        print('Add server {}:{}'.format(form.host.data, form.port.data))
        # return flask.redirect('/')
    return render_template('servers.html', form=form)
