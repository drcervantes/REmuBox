import virtualbox
import vboxapi
import subprocess
import logging
import socket
import string
import random
import sys
from contextlib import closing
from virtualbox import library
from .config_parser import get_templates

class WSUManager():
	def __init__(self):
		self.vbox = virtualbox.VirtualBox()

		temp_vbox = vboxapi.VirtualBoxManager()
		self.path_to_vb = temp_vbox.getBinDir() + "VBoxManage.exe"
		del temp_vbox


	def __enter__(self):
		return self


	def __exit__(self, exc_type, exc_value, traceback):
		del self.vbox


	def set_group(self, machine, group):
		"""Set the group for a virtual machine.

		Uses the python subprocess library to run VBoxManage because the pyvbox library has an 
		issue with modifying the groups of a machine.

	    Args:
	        machine (str): The name of the virtual machine.
	        group (str): The group the virtual machine should be a part of.

	    Returns:
	        
	    """
		result = subprocess.check_output([self.path_to_vb, "modifyvm", machine, "--groups", group])


	def get_random_intnet(self):
		return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(10))


	def get_first_snapshot(self, machine):
		if machine.snapshot_count < 1:
			raise Exception("No snapshot found for %s. Unable to clone!" % machine.name)

		return machine.find_snapshot("")


	def get_free_port(self):
		"""Briefly opens and closes a socket to obtain an available port through the 
		operating system. 

	    Args:

	    Returns:
	        A port number.
	    """
		with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
			s.bind(('', 0))
			return s.getsockname()[1]


	def clone_vm(self, machine, snapshot_name=None, clone_name=None, group=None):
		snapshot = self.get_first_snapshot(machine)
		if snapshot_name is not None:
			snapshot = machine.find_snapshot(snapshot_name)

		return machine.clone(snapshot.id_p, name=clone_name, groups=group)


	def clone_wsu(self, workshop_name):
		"""Clones a workshop unit from the corresponding template. Each cloned workshop 
		unit will be placed into a group with the following naming scheme <workshop>-Units.
		Each machine in the unit will be assigned a name unique to the server node:
		<machine name>_WSU_<group number>_<machine number>

	    Args:
	    	workshop_name (str): The name of the workshop.

	    Returns:
	        A string containing the group path for the cloned workshop unit.
	    """
		group_list = list(self.vbox.machine_groups)
		template_name = "/" + workshop_name + "-Template"
		logging.debug("Cloning template: " + template_name)
		
		if template_name not in group_list:
			raise Exception("Template %s was not found!" % template_name)

		group_base_name = "/" + workshop_name + '-Units/'

		extension = None
		for unit_number in range(0,1000):
			extension = "WSU_" + str(unit_number)
			if (group_base_name + extension) not in group_list:
				break

		if extension == None:
			raise Exception("Unable to find group space for WSU")

		wsu_path = group_base_name + extension

		machines = self.vbox.get_machines_by_groups([template_name,])
		machine_count = 0

		int_net = self.get_random_intnet()

		for machine in machines:
			clone = self.clone_vm(machine, group=[wsu_path,])
			
			session = clone.create_session()

			machine_name = machine.name + "_" + extension + "_" + str(machine_count)
			session.machine.name = machine_name
			logging.debug("Cloned machine: " + machine_name)
			
			adapter = session.machine.get_network_adapter(0)

			adapter.attachment_type = library.NetworkAttachmentType(3)
			adapter.internal_network = int_net
			logging.debug("Cloned machine intnet: " + int_net)		

			port = str(self.get_free_port())
			session.machine.vrde_server.set_vrde_property('TCP/Ports', port)
			logging.debug("Cloned machine port: " + port)

			session.machine.save_settings()
			session.unlock_machine()

			self.set_group(clone.name, wsu_path)
			machine_count += 1
		return wsu_path


	def add_vpn_rules(self, machine, name):
		session = machine.create_session()
		machine_name = name
		session.machine.name = machine_name
		
		tcp = virtualbox.library.NATProtocol(1)
		adapter = session.machine.get_network_adapter(0)
		nat_engine = adapter.nat_engine
		
		nat_engine.add_redirect('', tcp, '', self.get_free_port(), '', 1194)
		session.machine.save_settings()
		session.unlock_machine()

		
	def get_workshop_units(self, workshop_name):
		group_list = list(self.vbox.machine_groups)
		units = []
		for group in group_list:
			if group.find(workshop_name + "-Units") >= 0:
				units.append(group)
		return units


	def get_unit_count(self, workshop_name):
		return len(self.get_workshop_units(workshop_name))


	def find_available_unit(self, workshop_name):
		units = self.get_workshop_units(workshop_name)

		available_wsu = None
		for wsu in units:
			machines = self.vbox.get_machines_by_groups([wsu,])
			all_off = True
			for machine in machines:
				if machine.state >= library.MachineState.running:
					all_off = False
			if all_off:
				available_wsu = wsu
				break

		return available_wsu


	def start_wsu(self, group_name):
		logging.debug("Starting unit: " + group_name)
		machines = self.vbox.get_machines_by_groups([group_name,])
		for machine in machines:
			if machine.state < library.MachineState.running:
				logging.debug("Starting machine: " + machine.name)
				try:
					progress = machine.launch_vm_process(type_p="headless")
					progress.wait_for_completion()
				except Exception:
					logging.error("Error starting machine: " + machine.name)


	def save_wsu(self, group_name):
		logging.debug("Saving unit: " + group_name)
		machines = self.vbox.get_machines_by_groups([group_name,])
		for machine in machines:
			if machine.state >= library.MachineState.running:
				logging.debug("Saving machine: " + machine.name)
				try:
					session = machine.create_session()
					progress = session.machine.save_state()
					progress.wait_for_completion()
					session.unlock_machine()
				except Exception:
					logging.error("Error saving machine: " + machine.name)


	def stop_wsu(self, group_name, save=False):
		logging.debug("Stopping unit: " + group_name)
		machines = self.vbox.get_machines_by_groups([group_name,])
		for machine in machines:
			if machine.state >= library.MachineState.running:
				logging.debug("Stopping: " + machine.name)
				session = machine.create_session()
				try:
					if save:
						progress = session.machine.save_state()
						progress.wait_for_completion()
					else:
						progress = session.console.power_down()
						progress.wait_for_completion()
				except Exception:
					logging.error("Error stopping machine: " + machine.name)
				session.unlock_machine()


	def restore_wsu(self, group_name):
		logging.debug("Restoring unit: " + group_name)
		template = "/" + group_name.split('/')[1].split('-')[0] + "-Template"

		snapshots = {}
		machines = self.vbox.get_machines_by_groups([template,])
		for machine in machines:
			snapshots[machine.name] = self.get_first_snapshot(machine)

		machines = self.vbox.get_machines_by_groups([group_name,])
		for machine in machines:
			logging.debug("Restoring machine: " + machine.name)
			session = machine.create_session()
			try:
				ext_index = machine.name.find("_WSU")
				machine_name = machine.name[0:ext_index]
				progress = session.machine.restore_snapshot(snapshots[machine_name])
				progress.wait_for_completion()
				port = str(self.get_free_port())
				session.machine.vrde_server.set_vrde_property('TCP/Ports', port)
			except Exception:
				logging.error("Error restoring machine: " + machine.name)
			session.unlock_machine()


	def delete_wsu(self, group_name):
		logging.debug("Deleting unit: " + group_name)
		machines = self.vbox.get_machines_by_groups([group_name,])
		for machine in machines:
			logging.debug("Deleting machine: " + machine.name)
			try:
				machine.remove()
			except Exception:
				logging.error("Error deleting machine: " + machine.name)


	def progressBar(self, progress, wait=5000):
		try:
			while not progress.completed:
				print("%s %%\r" % (str(progress.percent)), end="")
				sys.stdout.flush()
				progress.wait_for_completion(wait)

		except KeyboardInterrupt:
			logging.error("Interrupted.")
			if progress.cancelable:
				logging.error("Canceling task...")
				progress.cancel()


	def import_wsu(self, config):
		logging.debug("Importing template: " + config["name"])

		appliance = self.vbox.create_appliance()
		appliance.read(config["appliance"])

		progress = appliance.import_machines()
		self.progressBar(progress)

		for machine_id in appliance.machines:
			machine = self.vbox.find_machine(machine_id)

			self.set_group(machine.name, "/" + config["name"] + "-Template")
			session = machine.create_session()
			progress, snap_id = session.machine.take_snapshot('WSU_Snap', 'Snapshot for creating workshop units.', False)
			progress.wait_for_completion()
			session.unlock_machine()


	def import_templates(self):
		"""Imports all appliances from the templates directory if they are not already imported
		into VirtualBox. 
	    """

		# Grab templates already imported
		existing_templates = []
		group_list = list(self.vbox.machine_groups)
		for group in group_list:
			idx = group.find("-Template")
			if idx > 0:
				existing_templates.append(group[1:idx])

		templates = [t for t in get_templates() if t["name"] not in existing_templates]

		for wsu in templates:
			self.import_wsu(wsu)
		

	def get_vm_stats(self, machine):
		stats = {}
		session = machine.create_session()
		stats["state"] = machine.state._value
		stats["vrde-enabled"] = session.machine.vrde_server.enabled
		if session.machine.vrde_server.enabled == 1 and machine.state == library.MachineState.running:
			vrde = session.console.vrde_server_info
			stats["vrde-active"] = vrde.active
			stats["vrde-port"] = vrde.port
			stats["vrde-start-time"] = vrde.begin_time
			stats["vrde-bytes-sent"] = vrde.bytes_sent
			stats["vrde-bytes-received"] = vrde.bytes_received
		session.unlock_machine()

		return stats


	def get_unit_stats(self, group_name):
		stats = {}
		machines = self.vbox.get_machines_by_groups([group_name,])
		for machine in machines:
			stats[machine.name] = self.get_vm_stats(machine)
		return stats


	def get_workshop_stats(self, workshop_name):
		stats = {}
		for unit in self.get_workshop_units(workshop_name):
			unit_name = unit.split("/")[2]
			stats[unit_name] = self.get_unit_stats(unit)
		return stats


	def get_vbox_stats(self):
		stats = {}
		workshops = [group for group in self.vbox.machine_groups if group.find("Template") > 0]
		for workshop in workshops:
			workshop_name = workshop.split("/")[1].split("-")[0]
			stats[workshop_name] = self.get_workshop_stats(workshop_name)
		return stats
