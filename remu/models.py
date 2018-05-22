from mongoengine import (
    Document, StringField, BooleanField, IntField, ListField, MapField,
    EmbeddedDocument, EmbeddedDocumentField, ReferenceField
    )
from flask_login import UserMixin

"""
    TODO: Apply constraints to the models.
"""

class Workshop(Document):
    name = StringField(unique=True)
    description = StringField()
    enabled = BooleanField()
    vpn_enabled = BooleanField()
    vpn_port = IntField()
    min_instances = IntField()
    max_instances = IntField()

class Session(EmbeddedDocument):
    workshop = ReferenceField(Workshop)
    ports = ListField(IntField())
    password = StringField()
    available = BooleanField()

class Server(Document):
    ip = StringField(unique=True)
    port = IntField()
    sessions = MapField(EmbeddedDocumentField(Session))

class User(UserMixin, Document):
    name = StringField()
    password = StringField()

    def get_id(self):
        return self.name

    def check_password(self, in_pass):
        return in_pass == self.name