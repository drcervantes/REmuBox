import pytest

import mongoengine as me
import os

from remu.models import *
from remu.database import *
from remu.importer import Templates
from remu.server import WorkshopManager


@pytest.fixture(scope='function')
def mongo(request):
   db = me.connect('testdb', host='mongomock://localhost')

   yield db

   db.drop_database('testdb')
   db.close()


@pytest.fixture(scope='function')
def server():
	insert_server('127.0.0.1', 9000)
	return Server.objects().first()


@pytest.fixture(scope='function')
def workshop():
	insert_workshop('test', '', 0, 0, True)
	return Workshop.objects().first()


@pytest.fixture(scope='class')
def importer(request):
	with Templates() as t:
		if request.cls is not None:
			request.cls.importer = t
			
		yield t


@pytest.fixture(scope='class')
def workshop_manager(request):
	mgr = WorkshopManager()

	if request.cls is not None:
		request.cls.mgr = mgr
		
	with Templates() as t:
		t.import_new()

	yield mgr

	mgr.remove_unit('/Test_Workshop-Template')
	mgr.clean_up()
	del mgr


@pytest.fixture(scope='function')
def machine(request):
	tc = request.cls.mgr.vbox.find_machine('TinyCore')
	clone = tc.clone()

	yield clone

	request.cls.mgr._delete_machine(clone)


@pytest.fixture(scope='function')
def unit(request):
	try:
		sid = request.param
	except AttributeError:
		sid = 'sid'

	request.cls.mgr.clone_unit('Test_Workshop', sid)
	yield
	request.cls.mgr.remove_unit(sid)
