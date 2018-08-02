from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField,
    FileField, TextAreaField, MultipleFileField
    )
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username    = StringField('Username', validators=[DataRequired()])
    password    = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit      = SubmitField('Log In')

class AddServerForm(FlaskForm):
    address = StringField('Address', validators=[DataRequired()])
    port    = StringField('Port', validators=[DataRequired()])
    submit  = SubmitField('Save')

class AddWorkshopForm(FlaskForm):
    name        = StringField('Workshop Folder', validators=[DataRequired()])
    display     = StringField('Displpay Name')
    description = TextAreaField('Description', validators=[DataRequired()])
    mini        = StringField('Min Instances', validators=[DataRequired()])
    maxi        = StringField('Max Instances', validators=[DataRequired()])
    materials   = MultipleFileField('Materials')
    enabled     = BooleanField('Enabled')
    submit      = SubmitField('Save')
