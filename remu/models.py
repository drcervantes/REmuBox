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
    min_instances = IntField()
    max_instances = IntField()
    walkthrough = StringField()

class Machine(EmbeddedDocument):
    name = StringField()
    port = IntField()
    active = BooleanField()
    start_time = IntField()

class Session(EmbeddedDocument):
    workshop = ReferenceField(Workshop)
    machines = ListField(EmbeddedDocumentField(Machine))
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
