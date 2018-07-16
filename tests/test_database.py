import pytest
from remu.models import *
from remu.database import *


@pytest.mark.usefixtures('mongo')
class TestDatabase:

	def test_insert_server_normal(self):
		insert_server('127.0.0.1', 9000)
		assert Server.objects.first().ip == '127.0.0.1'

	def test_insert_server_wrong_type(self):
		with pytest.raises(Exception):
			insert_server(0, 9000)

	def test_insert_server_empty_name(self):
		with pytest.raises(Exception):
			insert_server('', 9000)

	def test_insert_server_duplicate_name(self):
		with pytest.raises(Exception):
			insert_server('127.0.0.1', 9000)
			insert_server('127.0.0.1', 9000)

	def test_insert_server_invalid_range(self):
		with pytest.raises(Exception):
			insert_server('127.0.0.1', 100)


	def test_insert_workshop_normal(self):
		insert_workshop('test', '', 0, 0, True)
		assert Workshop.objects.first().name == 'test'

	def test_insert_workshop_wrong_type(self):
		with pytest.raises(Exception):
			insert_workshop(0, 0, 0, 0, True)

	def test_insert_workshop_empty_name(self):
		with pytest.raises(Exception):
			insert_workshop('', '', 0, 0, True)

	def test_insert_workshop_duplicate_name(self):
		with pytest.raises(Exception):
			insert_workshop('test', '', 0, 0, True)
			insert_workshop('test', '', 0, 0, True)

	def test_insert_workshop_invalid_range(self):
		with pytest.raises(Exception):
			insert_workshop('', '', -1, 0, True)


	def test_insert_session_normal(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		assert 'sid' in Server.objects().first().sessions

	def test_insert_session_wrong_type(self, server, workshop):
		with pytest.raises(Exception):
			insert_session(server.ip, 0, workshop.name, 0)

	def test_insert_session_empty_sid(self, server, workshop):
		with pytest.raises(Exception):
			insert_session(server.ip, '', workshop.name, 'pass')

	def test_insert_session_empty_pass(self, server, workshop):
		with pytest.raises(Exception):
			insert_session(server.ip, 'sid', workshop.name, '')

	def test_insert_session_duplicate(self, server, workshop):
		with pytest.raises(Exception):
			insert_session(server.ip, 'sid', workshop.name, 'pass')
			insert_session(server.ip, 'sid', workshop.name, 'pass')


	def test_insert_machine_normal(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		insert_machine(server.ip, 'sid', 'machine', 3000)
		s = Server.objects().first()
		assert s.sessions['sid'].machines[0].name == 'machine'

	def test_insert_machine_invalid_type(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		with pytest.raises(Exception):
			insert_machine(server.ip, 'sid', 0, 3000)

	def test_insert_machine_empty_name(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		with pytest.raises(Exception):
			insert_machine(server.ip, 'sid', '', 3000)

	def test_insert_machine_invalid_sid(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		with pytest.raises(Exception):
			insert_machine(server.ip, '', 'machine', 3000)


	def test_remove_server_normal(self, server):
		remove_server(server.ip)
		assert not Server.objects(ip=server.ip)

	def test_remove_server_empty_ip(self):
		with pytest.raises(Exception):
			remove_server('')

	def test_remove_server_invalid_ip(self):
		with pytest.raises(Exception):
			remove_server('fake')

	def test_remove_server_invalid_type(self):
		with pytest.raises(Exception):
			remove_server(0)


	def test_remove_workshop_normal(self, workshop):
		remove_workshop(workshop.id)
		assert not Workshop.objects(id=workshop.id)

	def test_remove_workshop_empty_oid(self):
		with pytest.raises(Exception):
			remove_workshop('')

	def test_remove_workshop_invalid_name(self):
		with pytest.raises(Exception):
			remove_workshop('fake')

	def test_remove_workshop_invalid_type(self):
		with pytest.raises(Exception):
			remove_workshop(0)


	def test_remove_session_normal(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		remove_session(server.ip, 'sid')
		assert 'sid' not in Server.objects().first().sessions

	def test_remove_session_empty_ip(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		with pytest.raises(Exception):
			remove_session('', 'sid')

	def test_remove_session_empty_sid(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		with pytest.raises(Exception):
			remove_session(server.ip, '')

	def test_remove_session_invalid_sid(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		with pytest.raises(Exception):
			remove_session(server.ip, 'fake')

	def test_remove_session_invalid_type(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		with pytest.raises(Exception):
			remove_session(server.ip, 0)


	def test_update_workshop_normal(self, workshop):
		update_workshop(workshop.id, name="update")
		assert Workshop.objects(id=workshop.id).first().name == "update"

	def test_update_workshop_empty_oid(self):
		with pytest.raises(Exception):
			update_workshop('', name="update")

	def test_update_workshop_invalid_oid(self):
		with pytest.raises(Exception):
			update_workshop('fake', name="update")


	def test_update_machines_normal(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		insert_machine(server.ip, 'sid', 'machine', 3000)
		update_machines(server.ip, 'sid', [{'vrde-active':True}])
		s = Server.objects().first()
		assert s.sessions['sid'].machines[0].vrde_active == True

	def test_update_machines_empty_ip(self):
		with pytest.raises(Exception):
			update_machines('', 'sid', [{'vrde-active':True}])

	def test_update_machines_empty_sid(self, server):
		with pytest.raises(Exception):
			update_machines(server.ip, '', [{'vrde-active':True}])


	def test_update_server_normal(self, server):
		update_server(server.ip, port=8080)
		assert Server.objects().first().port == 8080

	def test_update_server_invalid_port(self, server):
		with pytest.raises(Exception):
			update_server(server.ip, port=100)


	def test_update_session_normal(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		update_session(server.ip, 'sid', False)
		s = Server.objects().first()
		assert s.sessions['sid'].available == False

	
	def test_session_count_by_workshop_normal(self, server, workshop):
		insert_session(server.ip, 'sid', workshop.name, 'pass')
		assert session_count_by_workshop(workshop.name) == 1

		insert_server('other', 9000)
		insert_session('other', 'sid2', workshop.name, 'pass')
		assert session_count_by_workshop(workshop.name, ip=server.ip) == 1
		assert session_count_by_workshop(workshop.name, available=True) == 2


	# def test_session_to_workshop_count(self, server, workshop):
		