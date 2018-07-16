import pytest
import time

import virtualbox.library as vboxlib

from remu.server import WorkshopManager

@pytest.mark.workshop
@pytest.mark.usefixtures('workshop_manager')
class TestWorkshopManager:

	def test_delete_machine(self):
		tc = self.mgr.vbox.find_machine('TinyCore').clone()
		name = tc.name
		self.mgr._delete_machine(tc)
		machines = [m.name for m in self.mgr.vbox.machines]
		assert name not in machines


	def test_set_group(self, machine):
		self.mgr._set_group(machine.name, '/Test_Set_Group')
		assert '/Test_Set_Group' in self.mgr.vbox.machine_groups


	def test_get_first_snapshot(self, machine):
		session = machine.create_session()

		progress, first = session.machine.take_snapshot('first', 'desc', True)
		progress.wait_for_completion()

		progress, second = session.machine.take_snapshot('second', 'desc', True)
		progress.wait_for_completion()

		assert first == self.mgr._get_first_snapshot(session.machine).id_p

		progress = session.machine.delete_snapshot(second)
		progress.wait_for_completion()

		progress = session.machine.delete_snapshot(first)
		progress.wait_for_completion()
		
		session.unlock_machine()


	def test_get_recent_snapshot(self, machine):
		session = machine.create_session()

		progress, first = session.machine.take_snapshot('first', 'desc', True)
		progress.wait_for_completion()

		progress, second = session.machine.take_snapshot('second', 'desc', True)
		progress.wait_for_completion()

		assert second == self.mgr._get_recent_snapshot(session.machine).id_p

		progress = session.machine.delete_snapshot(second)
		progress.wait_for_completion()

		progress = session.machine.delete_snapshot(first)
		progress.wait_for_completion()
		
		session.unlock_machine()


	def test_get_free_port(self):
		port = self.mgr._get_free_port()
		assert port >= 1024 and port <= 65535


	def test_clone_vm(self):
		tc = self.mgr.vbox.find_machine('TinyCore')
		clone = self.mgr._clone_vm(tc)

		assert clone is not None

		self.mgr._delete_machine(clone)

	def test_clone_vm_recover_snapshot(self, machine):
		with pytest.raises(Exception):
			machine.find_snapshot("")

		clone = self.mgr._clone_vm(machine)
		assert clone is not None
		self.mgr._delete_machine(clone)


	def test_clone_unit(self):
		self.mgr.clone_unit('Test_Workshop', 'sid')
		unit = '/Test_Workshop-Units/sid'
		assert unit in self.mgr.vbox.machine_groups

		for m in self.mgr.vbox.get_machines_by_groups([unit]):
			self.mgr._delete_machine(m)

	def test_clone_unit_invalid_workshop(self):
		with pytest.raises(Exception):
			self.mgr.clone_unit('', 'sid')


	def test_get_all_units_by_workshop(self, unit):
		assert len(self.mgr._get_all_units_by_workshop('Test_Workshop')) > 0

	def test_get_all_units_by_workshop_invalid_group(self):
		assert self.mgr._get_all_units_by_workshop('fake') == []

	def test_get_all_units_by_workshop_empty_str(self):
		with pytest.raises(Exception):
			self.mgr._get_all_units_by_workshop('')


	def test_get_unit(self, unit):
		assert self.mgr._get_unit('sid') == '/Test_Workshop-Units/sid'

	def test_get_unit_invalid_name(self):
		assert self.mgr._get_unit('fake') == None

	def test_get_unit_empty_str(self):
		with pytest.raises(Exception):
			self.mgr._get_unit('')


	def test_get_unit_machines(self, unit):
		assert len(self.mgr._get_unit_machines('/Test_Workshop-Units/sid')) > 0

	def test_get_unit_machines_invalid_sid(self):
		with pytest.raises(Exception):
			self.mgr._get_unit_machines('fake')

	def test_get_unit_machines_empty_str(self):
		with pytest.raises(Exception):
			self.mgr._get_unit_machines('')


	def test_unit_to_str(self, unit):
		machines = self.mgr.unit_to_str('sid')
		assert machines[0]['name'] == 'TinyCore_sid'
		assert machines[0]['port'] == '1'

	def test_unit_to_str_invalid_sid(self):
		with pytest.raises(Exception):
			self.mgr.unit_to_str('fake')

	def test_unit_to_str_empty_str(self):
		with pytest.raises(Exception):
			self.mgr.unit_to_str('')


	@pytest.mark.parametrize('unit', ['start'], indirect=True)
	def test_start_unit(self, unit):
		self.mgr.start_unit('start')

		time.sleep(0.5)

		machines = self.mgr.vbox.get_machines_by_groups(['/Test_Workshop-Units/start'])

		for m in machines:
			assert m.state == vboxlib.MachineState.running

		for m in machines:
			session = m.create_session()
			progress = session.console.power_down()
			progress.wait_for_completion()
			session.unlock_machine()

		time.sleep(0.5)


	@pytest.mark.parametrize('unit', ['save'], indirect=True)
	def test_save_unit(self, unit):
		machines = self.mgr.vbox.get_machines_by_groups(['/Test_Workshop-Units/save'])
		for m in machines:
			progress = m.launch_vm_process(type_p="headless")
			progress.wait_for_completion()

		time.sleep(0.5)

		self.mgr.save_unit('save')

		for m in machines:
			assert m.state == vboxlib.MachineState.saved

		time.sleep(0.5)


	@pytest.mark.parametrize('unit', ['stop'], indirect=True)
	def test_stop_unit(self, unit):
		machines = self.mgr.vbox.get_machines_by_groups(['/Test_Workshop-Units/stop'])
		for m in machines:
			progress = m.launch_vm_process(type_p="headless")
			progress.wait_for_completion()

		time.sleep(0.5)

		self.mgr.stop_unit('stop')

		time.sleep(0.5)

		for m in machines:
			assert m.state == vboxlib.MachineState.powered_off


	def test_restore_unit(self):
		self.mgr.clone_unit('Test_Workshop', 'restore')

		time.sleep(0.5)

		machines = self.mgr.vbox.get_machines_by_groups(['/Test_Workshop-Units/restore'])
		for m in machines:
			progress = m.launch_vm_process(type_p="headless")
			progress.wait_for_completion()

		time.sleep(0.5)

		for m in machines:
			session = m.create_session()
			progress = session.machine.save_state()
			progress.wait_for_completion()
			session.unlock_machine()

		time.sleep(0.5)

		self.mgr.restore_unit('restore', 'after')

		time.sleep(0.5)

		for m in machines:
			assert m.state == vboxlib.MachineState.powered_off
			assert 'after' in m.name
			assert 'after' in m.groups[0]

			self.mgr._delete_machine(m)


	def test_remove_unit(self):
		self.mgr.clone_unit('Test_Workshop', 'remove')

		time.sleep(0.5)

		self.mgr.remove_unit('remove')

		assert 'TinyCore_remove' not in [m.name for m in self.mgr.vbox.machines]
		assert '/Test_Workshop-Units/remove' not in self.mgr.vbox.machine_groups


	def test_get_workshop_list(self):
		assert len(self.mgr.get_workshop_list()) > 0