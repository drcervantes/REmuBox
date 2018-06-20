import logging
import socket
import subprocess
import contextlib

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
        self.vbox = virtualbox.VirtualBox()

    def _set_group(self, machine, group):
        """Set the group for a virtual machine."""
        return subprocess.check_output([config['REMU']['vbox_manage'], "modifyvm", machine, "--groups", group])

    def _get_first_snapshot(self, machine):
        if machine.snapshot_count < 1:
            raise Exception("No snapshot found for %s. Unable to clone!" % machine.name)

        return machine.find_snapshot("")

    def _get_free_port(self):
        """Briefly opens and closes a socket to obtain an available port through the 
        operating system. 
        """
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.bind(('', 0))
            return sock.getsockname()[1]

    def _get_all_units_by_workshop(self, workshop_name):
        group_list = list(self.vbox.machine_groups)
        units = []
        for group in group_list:
            if group.find(workshop_name + "-Units") >= 0:
                units.append(group)
        return units

    def _get_unit(self, session):
        """Get a workshop unit's group path by session id."""
        groups = list(self.vbox.machine_groups)
        for g in groups:
            if g.find(session) >= 0:
                return g
        return None

    def _get_unit_machines(self, unit):
        """Get all machines in a specific unit."""
        return self.vbox.get_machines_by_groups([unit,])

    def _clone_vm(self, machine, snapshot_name=None, clone_name=None, group=None):
        snapshot = self._get_first_snapshot(machine)
        if snapshot_name is not None:
            snapshot = machine.find_snapshot(snapshot_name)

        return machine.clone(snapshot.id_p, name=clone_name, groups=group)

    def clone_unit(self, workshop, session_id):
        """Clones a workshop unit from the corresponding template. Each cloned workshop 
        unit will be placed into a group with the following naming scheme <workshop>-Units.
        """
        group_list = list(self.vbox.machine_groups)
        template = "/" + workshop + "-Template"
        l.info("Cloning template: %s", template)

        if template not in group_list:
            raise Exception("Template for %s was not found!" % workshop)

        clones = []
        int_net = rand_str(10)
        unit_path = "/" + workshop + '-Units/' + session_id

        for machine in self._get_unit_machines(template):
            clone = self._clone_vm(machine, group=[unit_path,])
            
            try:
                session = clone.create_session(vboxlib.LockType(2))

                machine_name = machine.name + "_" + session_id
                session.machine.name = machine_name
                l.info("Cloned machine: %s", machine_name)
                
                adapter = session.machine.get_network_adapter(0)

                adapter.attachment_type = vboxlib.NetworkAttachmentType(3)
                adapter.internal_network = int_net
                l.info(" ... intnet: %s", int_net)     

                if session.machine.vrde_server.enabled:
                    port = str(self._get_free_port())
                    l.info(" ... vrde port: %s", port)
                else:
                    port = "1"
                    l.info(" ... vrde not enabled")
                session.machine.vrde_server.set_vrde_property('TCP/Ports', port)

                # session.machine.save_settings()
                progress, sid = session.machine.take_snapshot("Original", "Original state of the machine.", True)
                progress.wait_for_completion()
                session.unlock_machine()

                self._set_group(clone.name, unit_path)
                clones.append(machine)
            except Exception as e:
                msg = "Error cloning: {}".format(machine.name)
                l.error(msg)
                for c in clones:
                    c.remove()
                raise Exception(msg)

        return unit_path

    def unit_to_str(self, session):
        path = self._get_unit(session)
        machines = []
        for m in self._get_unit_machines(path):
            machines.append({
                'name': m.name,
                'port': m.vrde_server.get_vrde_property('TCP/Ports')
            })
        return machines

    def start_unit(self, sid):
        unit = self._get_unit(sid)
        l.info("Starting unit: %s", unit)
        for machine in self._get_unit_machines(unit):
            if machine.state == vboxlib.MachineState(1) or \
               machine.state == vboxlib.MachineState(2):
                l.info(" ... starting machine: %s", machine.name)
                try:
                    progress = machine.launch_vm_process(type_p="headless")
                    progress.wait_for_completion()
                except Exception:
                    l.exception("Fatal error starting machine: %s", machine.name)
                    return False
            else:
                l.error("Error starting machine: %s. Machine is not powered off or saved.", machine.name)
                return False
        return True

    def save_unit(self, sid):
        unit = self._get_unit(sid)
        l.info("Saving unit: %s", unit)

        for machine in self._get_unit_machines(unit):
            if machine.state == vboxlib.MachineState(5):
                l.info(" ... saving machine: %s", machine.name)
                try:
                    session = machine.create_session()
                    progress = session.machine.save_state()
                    progress.wait_for_completion()
                    session.unlock_machine()
                except Exception:
                    l.exception("Fatal error saving machine: %s", machine.name)
                    return False
            else:
                l.error("Error saving machine: %s. Machine is not running.", machine.name)
                return False
        return True

    def stop_unit(self, sid):
        unit = self._get_unit(sid)
        l.info("Stopping unit: %s", unit)
        for machine in self._get_unit_machines(unit):
            if machine.state == vboxlib.MachineState(5):
                l.info(" ... stopping machine: %s", machine.name)
                try:
                    session = machine.create_session()
                    progress = session.console.power_down()
                    progress.wait_for_completion()
                    session.unlock_machine()
                except Exception:
                    l.exception("Fatal error stopping machine: %s", machine.name)
                    return False
            else:
                l.error("Error stopping machine: %s. Machine is not running.", machine.name)
                return False
        return True

    def restore_unit(self, sid, new_sid):
        unit = self._get_unit(sid)
        l.info("Restoring unit: %s", unit)
        for machine in self._get_unit_machines(unit):
            if machine.state == vboxlib.MachineState(1) or \
               machine.state == vboxlib.MachineState(2):
                l.info(" ... restoring machine: %s", machine.name)
                try:
                    # Obtain snapshot of the original state
                    snapshot = self._get_first_snapshot(machine)

                    # Restore the machine
                    session = machine.create_session()
                    progress = session.machine.restore_snapshot(snapshot)
                    progress.wait_for_completion()

                    # Change the machine name
                    name = session.machine.name
                    base_end = name.rfind('_') + 1
                    name = name[:base_end] + new_sid
                    session.machine.name = name
                    l.debug(" ... new machine name: %s", name)

                    session.unlock_machine()

                    # Change the session id in the group name
                    group = machine.groups[0]
                    base_end = group.rfind('/') + 1
                    group = group[:base_end] + new_sid
                    l.debug(" ... new group name: %s, group")
                    self._set_group(machine.name, group)
                except Exception:
                    l.error("Error restoring machine: %s", machine.name)
            else:
                l.error("Error restoring machine: %s. Machine is not powered off or saved.", machine.name)
                return False
        return True

    def remove_unit(self, unit):
        l.debug("Deleting unit: %s", unit)
        machines = self.vbox.get_machines_by_groups([unit,])
        for machine in machines:
            l.debug("Deleting machine: %s", machine.name)
            try:
                machine.remove()
            except Exception:
                l.error("Error deleting machine: %s", machine.name)

    def get_workshop_list(self):
        """Provides a list of all workshop names available on the server node."""
        workshops = []

        for group in self.manager.vbox.machine_groups:
            idx = group.find("-Template")
            if idx > 0: 
                workshops.append(group[1:idx])

        return workshops

# class WorkshopManagerRemote():
#     def __init__(self, ip, port):
#         self.ip = ip
#         self.port = port

    def start_unit(self, sid):
        url = remote.build_url(self.ip, self.port, "start_unit", session=sid)
        try:
            r = requests.get(url)
            r.raise_for_status()
            return r.text
        except requests.exceptions.HTTPError:
            l.exception("")
        

#         return

    # def save_unit(self, sid)
    # def stop_unit(self, sid)
    # def restore_unit(self, sid, new_sid)
    # def remove_unit(self, sid)