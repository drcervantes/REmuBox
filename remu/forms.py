from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')

class AddServerForm(FlaskForm):
    host = StringField('Host', validators=[DataRequired()])
    port = StringField('Port', validators=[DataRequired()])
    submit = SubmitField('Add Server')