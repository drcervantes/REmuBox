"""
Notes:
Start performance collecting when starting a machine
... setup_metrics needs to be called after machine is running
When removing the machine, may need to remove snapshot first
"""
import logging
import socket
import subprocess
import contextlib
import pathlib
import virtualbox
import virtualbox.library as vboxlib
import psutil

from remu.util import rand_str
from remu.settings import config

l = logging.getLogger('default')

class WorkshopManager():
    def __init__(self):
        l.info("WorkshopManager module starting...")
        self.vbox = virtualbox.VirtualBox()

    def clean_up(self):
        l.info(" ... WorkshopManager cleaning up")
        del self.vbox

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
        """
        Clones a workshop unit from the corresponding template. Each cloned workshop
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
                l.exception(msg)
                for c in clones:
                    c.remove()
                return False

        return True

    def unit_to_str(self, sid):
        path = self._get_unit(sid)

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
        l.info(" ... new session id: %s", new_sid)

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
                    l.debug(" ... new group name: %s", group)
                    self._set_group(machine.name, group)
                except Exception:
                    l.exception("Error restoring machine: %s", machine.name)
                    return False
            else:
                l.error("Error restoring machine: %s. Machine is not powered off or saved.", machine.name)
                return False
        return True

    def remove_unit(self, sid):
        unit = self._get_unit(sid)
        l.info("Removing unit: %s", sid)

        for machine in self._get_unit_machines(unit):
            if machine.state == vboxlib.MachineState(1) or \
               machine.state == vboxlib.MachineState(2):
                l.info(" ... removing machine: %s", machine.name)
                try:
                    snapshot = self._get_first_snapshot(machine)
                    machine.delete_snapshot(snapshot.id_p)
                    machine.remove()
                except Exception:
                    l.exception("Error removing machine: %s", machine.name)
                    return False
            else:
                l.error("Error removing machine: %s. Machine is not powered off or saved.", machine.name)
                return False
        return True

    def get_workshop_list(self):
        """Provides a list of all workshop names available on the server node."""
        workshops = []

        for group in self.vbox.machine_groups:
            idx = group.find("-Template")
            if idx > 0:
                workshops.append(group[1:idx])

        return workshops


class PerformanceMonitor():
    def __init__(self):
        l.info("PerformanceMonitor module starting...")

        # Obtain the performance collector built into virtual box
        self._vbox = virtualbox.VirtualBox()
        self._vms = self._vbox.performance_collector
        self._vms.setup_metrics(["*"], [], 10, 15)

        # Get the file path to the location where new virtual machines
        # will be created by virtualbox
        base_folder = self._vbox.compose_machine_filename('dummy', '/', '', '')
        path = pathlib.Path(base_folder)

        # Obtain physical devices
        try:
            mounts = psutil.disk_partitions(all=False)
        except UnicodeDecodeError:
            l.exception("Unable to determine the physical devices of the machine.")

        # Find which storage device contains the virtual machines
        for m in mounts:
            if m.mountpoint == path.anchor:
                self.mount = m.mountpoint
                l.debug("Mount containing VMs: %s", self.mount)
                break

    def clean_up(self):
        l.info(" ... PerformanceMonitor cleaning up")
        del self._vbox

    def update(self):
        updates = {}

        # Hard disk memory
        usage = psutil.disk_usage(self.mount)
        updates["hdd"] = usage.percent

        # CPU usage
        updates["cpu"] = psutil.cpu_percent()

        # RAM
        updates["mem"] = psutil.virtual_memory().percent

        updates["sessions"] = {}
        for g in self._vbox.machine_groups:
            if "Template" not in g:
                sid = g.split("/")[-1]
                updates["sessions"][sid] = []
                for m in self._vbox.get_machines_by_groups([g]):
                    updates["sessions"][sid].append(self._get_vm_stats(m))

        return updates

    def _get_vm_stats(self, machine):
        stats = {}

        session = machine.create_session()
        stats["state"] = machine.state._value
        stats["vrde-enabled"] = session.machine.vrde_server.enabled

        # VRDE must be enabled and the machine must be running
        if session.machine.vrde_server.enabled == 1 and machine.state == vboxlib.MachineState(5):
            vrde = session.console.vrde_server_info
            stats["vrde-active"] = bool(vrde.active)
        session.unlock_machine()

        """
        metrics = self._query_metrics(["*"], [machine])

        if not metrics:
            return None

        stats = {
            "cpu": (100000 - metrics["Guest/CPU/Load/Idle:avg"]["values"][0]) / 1000,
            "mem_free": metrics["Guest/RAM/Usage/Free:avg"]["values"][0],
            "mem_total": metrics["Guest/RAM/Usage/Total:avg"]["values"][0]
        }
        """

        return stats

    def _query_metrics(self, names, objects):
        """
        Retrieves collected metric values as well as some auxiliary
        information. Returns an array of dictionaries, one dictionary per
        metric. Each dictionary contains the following entries:
        'name': metric name
        'object': managed object this metric associated with
        'unit': unit of measurement
        'scale': divide 'values' by this number to get float numbers
        'values': collected data
        'values_as_string': pre-processed values ready for 'print' statement
        """

        (values, names_out, objects_out, units, scales, 
            sequence_numbers, indices, lengths) = self._vms.query_metrics_data(names, objects)
        out = {}
        for i in range(0, len(names_out)):
            scale = int(scales[i])
            if scale != 1:
                fmt = '%.2f%s'
            else:
                fmt = '%d %s'
            metric_name = str(names_out[i])
            out[metric_name] = {
                'object': str(objects_out[i]),
                'unit': str(units[i]),
                'scale': scale,
                'values': [int(values[j]) for j in range(int(indices[i]), int(indices[i]) + int(lengths[i]))],
                'values_as_string': '[' + ', '.join([fmt % (int(values[j]) / scale, units[i]) for j in
                                                     range(int(indices[i]), int(indices[i]) + int(lengths[i]))]) + ']'
            }
        return out
