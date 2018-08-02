from mongoengine import (
    Document, StringField, BooleanField, IntField, ListField, MapField,
    EmbeddedDocument, EmbeddedDocumentField, ReferenceField, FloatField
    )
from flask_login import UserMixin


class Workshop(Document):
    name = StringField(unique=True, required=True)
    display = StringField()
    description = StringField()
    enabled = BooleanField(required=True)
    min_instances = IntField(min_value=0, required=True)
    max_instances = IntField(min_value=0, required=True)

class Machine(EmbeddedDocument):
    name = StringField()
    port = IntField(min_value=1, max_value=65535)
    state = IntField(default=1)
    vrde_active = BooleanField(default=False)
    vrde_enabled = BooleanField(default=False)

class Session(EmbeddedDocument):
    workshop = ReferenceField(Workshop, required=True)
    machines = ListField(EmbeddedDocumentField(Machine))
    password = StringField(required=True)
    available = BooleanField(required=True)
    start_time = FloatField()

class Server(Document):
    ip = StringField(unique=True, required=True)
    port = IntField(min_value=1024, max_value=65535, required=True)
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
