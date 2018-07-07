from mongoengine import (
    Document, StringField, BooleanField, IntField, ListField, MapField,
    EmbeddedDocument, EmbeddedDocumentField, ReferenceField, FloatField
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

class Machine(EmbeddedDocument):
    name = StringField()
    port = IntField()
    state = IntField(default=1)
    vrde_active = BooleanField(default=False)
    vrde_enabled = BooleanField(default=False)

class Session(EmbeddedDocument):
    workshop = ReferenceField(Workshop)
    machines = ListField(EmbeddedDocumentField(Machine))
    password = StringField()
    available = BooleanField()
    start_time = FloatField()

class Server(Document):
    ip = StringField(unique=True)
    port = IntField()
    sessions = MapField(EmbeddedDocumentField(Session))
    cpu = FloatField()
    hdd = FloatField()
    mem = FloatField()

class User(UserMixin, Document):
    name = StringField()
    password = StringField()

    def get_id(self):
        return self.name

    def check_password(self, in_pass):
        return in_pass == self.name
