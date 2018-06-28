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
    submit  = SubmitField('Add Server')

class AddWorkshopForm(FlaskForm):
    name        = StringField('Workshop Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    mini        = StringField('Min Instances', validators=[DataRequired()])
    maxi        = StringField('Max Instances', validators=[DataRequired()])
    documents   = MultipleFileField('Supporting Documents', validators=[DataRequired()])
    enabled     = BooleanField('Enabled')
    submit      = SubmitField('Add Workshop')
