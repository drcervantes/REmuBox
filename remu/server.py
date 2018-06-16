import logging
import virtualbox

from remu.importer import import_new_templates
from remu.workshop import WorkshopManager
from remu.settings import config

"""
Things that need to be done:
    1. Ensure the values returned when starting a unit is what we need.
    2. Start and stop via session
    4. Use glances to obtain server state.
"""

l = logging.getLogger('default')

class Server():
    def __init__(self):
        self.vbox = virtualbox.VirtualBox()
        self.manager = WorkshopManager(self.vbox)

    def __del__(self):
        # TODO: need to clean up files left from machines
        del self.vbox
        del self.manager

    def import_templates(self):
        import_new_templates()

    def start(self, session, save=False):
        try:
            path = self.manager.get_unit(session)
            self.manager.start_unit(path)

            if save:
                self.manager.save_unit(path)
        except Exception as e:
            return False
        return True

    def clone(self, workshop, session):
        """Clones a workshop unit and returns a list of ports for all VRDE enabled machines."""
        unit = self.manager.clone_unit(workshop, session)

        ports = []
        for machine in self.manager.get_unit_machines(unit):
            if machine.vrde_server.enabled:
                port = machine.vrde_server.get_vrde_property('TCP/Ports')
                ports.append(port)
        return ports

    # def stop_unit(self, ports):
    #     """Session folder needs to be deleted"""
    #     unit = request.args.get("unit")
    #     if unit is None:
    #         logging.error("Error stopping unit: no name provided.")
    #         return
    #     split = unit.find("WSU")
    #     workshop_name = unit[0:split-1]
    #     extension = unit[split:]
    #     unit_path = "/" + workshop_name + "-Units/" + extension

    #     remove = request.args.get("remove")
    #     if remove is None:
    #         remove = 'True'

    #     try:
    #         self.manager.stop_wsu(unit_path)
    #         if remove == 'True':
    #             self.manager.delete_wsu(unit_path)
    #         else:
    #             self.manager.restore_wsu(unit_path)
    #     except Exception:
    #         logging.error("Error stopping unit: " + unit_path)
    #         return "FAILURE"

    #     return "SUCCESS"

    def unit_to_str(self, session):
        path = self.manager.get_unit(session)
        machines = []
        for m in self.manager.get_unit_machines(path):
            machines.append({
                'name': m.name,
                'port': m.vrde_server.get_vrde_property('TCP/Ports')
            })
        return machines

    # def get_workshop_list(self):
    #     """Provides a list of all workshop names available on the server node."""
    #     workshops = []

    #     for group in self.manager.vbox.machine_groups:
    #         idx = group.find("-Template")
    #         if idx > 0: 
    #             workshops.append(group[1:idx])

    #     return json.dumps(workshops)

    '''
    {'Route_Hijacking': {'WSU_0': {'kali-2016.2-debian_ecel_rh_WSU_0_0': {'state': MachineState(5),
                                                                          'vrde-active': 0,
                                                                          'vrde-bytes-received': 0,
                                                                          'vrde-bytes-sent': 0,
                                                                          'vrde-enabled': 1,
                                                                          'vrde-port': 56557,
                                                                          'vrde-start-time': 0},
                                   'ubuntu-core4.7_WSU_0_1': {'state': MachineState(5),
                                                              'vrde-enabled': 0}},
                         'WSU_1': {'kali-2016.2-debian_ecel_rh_WSU_1_0': {'state': MachineState(5),
                                                                          'vrde-active': 0,
                                                                          'vrde-bytes-received': 0,
                                                                          'vrde-bytes-sent': 0,
                                                                          'vrde-enabled': 1,
                                                                          'vrde-port': 56559,
                                                                          'vrde-start-time': 0},
                                   'ubuntu-core4.7_WSU_1_1': {'state': MachineState(5),
                                                              'vrde-enabled': 0}}}}
    '''
    def vbox_stats(self):
        return json.dumps(self.manager.get_vbox_stats())


# from glances.stats import GlancesStats
# stats = GlancesStats
# stats.getCpu()

# from glances.main import GlancesMain
# main = GlancesMain()
# main.args.disable_alert = True
# main.args.disable_amps = True
# main.args.disable_batpercent = True
# main.args.disable_cloud = True
# main.args.disable_core = True
# main.args.disable_diskio = True
# main.args.disable_docker = True
# main.args.disable_folders = True
# main.args.disable_fs = True
# main.args.disable_help = True
# main.args.disable_irq = True
# main.args.disable_load = True
# main.args.disable_processcount = True
# main.args.disable_processlist = True
# main.args.disable_psutilversion = True
# main.args.disable_raid = True
# main.args.disable_sensors = True
# main.args.disable_system = True
# main.args.disable_wifi = True

# stats = GlancesStats(main.config,main.args)
# stats.update()
# stats.getAllAsDict()