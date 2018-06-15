import logging
import socket
import subprocess
import sys
import contextlib

import xml.etree.ElementTree as et
import os

import virtualbox
import virtualbox.library as vboxlib
from remu.util import rand_str
from remu.settings import config

l = logging.getLogger('default')

"""
Notes:
Restoring needs to be finished
When removing the machine, may need to remove snapshot first
"""

class WorkshopManager():
    def __init__(self):
        self.vbox_path = config['REMU']['vbox_manage']
        self.vbox = virtualbox.VirtualBox()

    def __del__(self):
        del self.vbox

    def set_group(self, machine, group):
        """Set the group for a virtual machine."""
        return subprocess.check_output([self.vbox_path, "modifyvm", machine, "--groups", group])

    def get_first_snapshot(self, machine):
        if machine.snapshot_count < 1:
            raise Exception("No snapshot found for %s. Unable to clone!" % machine.name)

        return machine.find_snapshot("")

    def get_free_port(self):
        """Briefly opens and closes a socket to obtain an available port through the 
        operating system. 
        """
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.bind(('', 0))
            return sock.getsockname()[1]

    def clone_vm(self, machine, snapshot_name=None, clone_name=None, group=None):
        snapshot = self.get_first_snapshot(machine)
        if snapshot_name is not None:
            snapshot = machine.find_snapshot(snapshot_name)

        return machine.clone(snapshot.id_p, name=clone_name, groups=group)

    def clone_unit(self, workshop, session_id):
        """Clones a workshop unit from the corresponding template. Each cloned workshop 
        unit will be placed into a group with the following naming scheme <workshop>-Units.
        """
        group_list = list(self.vbox.machine_groups)
        template = "/" + workshop + "-Template"
        l.debug("Cloning template: %s", template)

        if template not in group_list:
            raise Exception("Template for %s was not found!" % workshop)

        clones = []
        int_net = rand_str(10)
        unit_path = "/" + workshop + '-Units/' + session_id

        for machine in self.get_unit_machines(template):
            clone = self.clone_vm(machine, group=[unit_path,])
            
            try:
                session = clone.create_session(vboxlib.LockType(2))

                machine_name = machine.name + "_" + session_id
                session.machine.name = machine_name
                l.debug("Cloned machine: %s", machine_name)
                
                adapter = session.machine.get_network_adapter(0)

                adapter.attachment_type = vboxlib.NetworkAttachmentType(3)
                adapter.internal_network = int_net
                l.debug(" ... intnet: %s", int_net)     

                if session.machine.vrde_server.enabled:
                    port = str(self.get_free_port())
                    l.debug(" ... vrde port: %s", port)
                else:
                    port = "0"
                    l.debug(" ... vrde not enabled")
                session.machine.vrde_server.set_vrde_property('TCP/Ports', port)

                # session.machine.save_settings()
                progress, sid = session.machine.take_snapshot("Original", "Original state of the machine.", True)
                progress.wait_for_completion()
                session.unlock_machine()

                self.set_group(clone.name, unit_path)
                clones.append(machine)
            except Exception as e:
                msg = "Error cloning: {}".format(machine.name)
                l.error(msg)
                for c in clones:
                    c.remove()
                raise Exception(msg)

        return unit_path

    def get_workshop_units(self, workshop_name):
        group_list = list(self.vbox.machine_groups)
        units = []
        for group in group_list:
            if group.find(workshop_name + "-Units") >= 0:
                units.append(group)
        return units

    def get_unit(self, session):
        """Get a workshop unit's group path by session id."""
        groups = list(self.vbox.machine_groups)
        for g in groups:
            if g.find(session) >= 0:
                return g
        return None

    def get_unit_machines(self, unit):
        """Get all machines in a specific unit."""
        return self.vbox.get_machines_by_groups([unit,])

    def start_unit(self, unit):
        l.debug("Starting unit: %s", unit)
        for machine in self.get_unit_machines(unit):
            if machine.state < vboxlib.MachineState.running:
                l.debug("Starting machine: " + machine.name)
                try:
                    progress = machine.launch_vm_process(type_p="headless")
                    progress.wait_for_completion()
                except Exception:
                    l.error("Error starting machine: %s", machine.name)

    def save_unit(self, unit):
        l.debug("Saving unit: " + unit)
        for machine in self.get_unit_machines(unit):
            if machine.state >= vboxlib.MachineState.running:
                l.debug("Saving machine: " + machine.name)
                try:
                    session = machine.create_session()
                    progress = session.machine.save_state()
                    progress.wait_for_completion()
                    session.unlock_machine()
                except Exception:
                    l.error("Error saving machine: %s", machine.name)

    def stop_unit(self, unit):
        l.debug("Stopping unit: %s", unit)
        for machine in self.get_unit_machines(unit):
            if machine.state >= vboxlib.MachineState.running:
                l.debug("Stopping: " + machine.name)
                try:
                    session = machine.create_session()
                    progress = session.console.power_down()
                    progress.wait_for_completion()
                    session.unlock_machine()
                except Exception:
                    l.error("Error stopping machine: %s", machine.name)   

    def restore_unit(self, unit):
        l.debug("Restoring unit: %s", unit)
        for machine in self.get_unit_machines(unit):
            l.debug("Restoring machine: %s", machine.name)
            try:
                snapshot = self.get_first_snapshot(machine)
                session = machine.create_session()
                progress = session.machine.restore_snapshot(snapshot)
                progress.wait_for_completion()
            except Exception:
                l.error("Error restoring machine: %s", machine.name)
            session.unlock_machine()

    def delete_unit(self, unit):
        l.debug("Deleting unit: %s", unit)
        machines = self.vbox.get_machines_by_groups([unit,])
        for machine in machines:
            l.debug("Deleting machine: %s", machine.name)
            try:
                machine.remove()
            except Exception:
                l.error("Error deleting machine: %s", machine.name)

    def get_vm_stats(self, machine):
        stats = {}
        session = machine.create_session()
        stats["state"] = machine.state._value
        stats["vrde-enabled"] = session.machine.vrde_server.enabled
        if session.machine.vrde_server.enabled == 1 and machine.state == vboxlib.MachineState.running:
            vrde = session.console.vrde_server_info
            stats["vrde-active"] = vrde.active
            stats["vrde-port"] = vrde.port
            stats["vrde-start-time"] = vrde.begin_time
            stats["vrde-bytes-sent"] = vrde.bytes_sent
            stats["vrde-bytes-received"] = vrde.bytes_received
        session.unlock_machine()
        return stats

    def get_unit_stats(self, unit):
        stats = {}
        machines = self.vbox.get_machines_by_groups([unit,])
        for machine in machines:
            stats[machine.name] = get_vm_stats(machine)
        return stats

    def get_workshop_stats(self, workshop_name):
        stats = {}
        for unit in get_workshop_units(workshop_name):
            unit_name = unit.split("/")[2]
            stats[unit_name] = get_unit_stats(unit)
        return stats

    def get_vbox_stats(self):
        stats = {}
        workshops = [group for group in self.vbox.machine_groups if group.find("Template") > 0]
        for workshop in workshops:
            workshop_name = workshop.split("/")[1].split("-")[0]
            stats[workshop_name] = get_workshop_stats(workshop_name)
        return stats

    def _parse_config(self, config_file):
        tree = et.parse(config_file)
        root = tree.getroot().find("workshop-settings")

        # Create a dictionary of all elements in the root
        workshop = {child.tag:child.text.strip() for child in root.getchildren() if not bool(child.getchildren())}

        # Create a list of dictionaries containing the elements within the vm tag
        vms = [{child.tag:child.text.strip() for child in vm.getchildren()} for vm in root.findall("vm")]
        workshop["vms"] = vms

        return workshop

    def get_templates(self, template_dir):
        workshops = []

        for workshop_dir in os.listdir(template_dir):
            config_path = os.path.join(template_dir, workshop_dir, "config.xml")
            workshop = self._parse_config(config_path)

            # Get the full path of the appliance for importing later
            workshop["appliance"] = os.path.join(os.getcwd(), template_dir, workshop_dir, workshop["appliance"])
            workshops.append(workshop)

        return workshops

    def _progress_bar(self, progress, wait=5000):
        try:
            while not progress.completed:
                print("Completion: %s %%\r" % (str(progress.percent)), end="")
                sys.stdout.flush()
                progress.wait_for_completion(wait)

        except KeyboardInterrupt:
            l.error("Interrupted.")
            if progress.cancelable:
                l.error("Canceling task...")
                progress.cancel()

    def _import_wsu(self, template):
        l.debug("Importing template: " + template["name"])

        appliance = self.vbox.create_appliance()
        appliance.read(template["appliance"])

        progress = appliance.import_machines()
        self._progress_bar(progress)

        for machine_id in appliance.machines:
            machine = self.vbox.find_machine(machine_id)
            l.debug(" ... importing machine: %s", machine.name)

            self.set_group(machine.name, "/" + template["name"] + "-Template")
            session = machine.create_session()
            progress, dummy = session.machine.take_snapshot('WSU_Snap', 'Snapshot for creating workshop units.', False)
            progress.wait_for_completion()
            session.unlock_machine()
        l.debug("%s imported successfully", template["name"])

    def import_templates(self):
        """
        Imports all appliances from the templates directory if they are not already imported
        into VirtualBox.
        """
        # Grab templates already imported
        existing_templates = []
        group_list = list(self.vbox.machine_groups)
        for group in group_list:
            idx = group.find("-Template")
            if idx > 0:
                existing_templates.append(group[1:idx])

        path = config['REMU']['workshops']
        templates = [t for t in self.get_templates(path) if t["name"] not in existing_templates]

        for wsu in templates:
            self._import_wsu(wsu)
