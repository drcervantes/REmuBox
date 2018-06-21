import logging
import virtualbox

from glances.main import GlancesMain
from glances.stats import GlancesStats

from remu.settings import config

l = logging.getLogger('default')

class Monitor():
    def __init__(self):
        self.recycle = []

    def start(self):
        # Get active session
        active = db.get_active_sessions()
        
        # check matching unit on server for active vrde connections
        # if no active connections, place in list to recycle
        # if active, make sure session is not in recycle list
        # go through recycle list and check if enough time has passed


class Hardware():
    def __init__(self):
        main = GlancesMain()

        # Disable all plugins not being utilized to improve performance
        main.args.disable_alert = True
        main.args.disable_amps = True
        main.args.disable_batpercent = True
        main.args.disable_cloud = True
        main.args.disable_core = True
        main.args.disable_diskio = True
        main.args.disable_docker = True
        main.args.disable_folders = True
        main.args.disable_fs = True
        main.args.disable_help = True
        main.args.disable_irq = True
        main.args.disable_load = True
        main.args.disable_processcount = True
        main.args.disable_processlist = True
        main.args.disable_psutilversion = True
        main.args.disable_raid = True
        main.args.disable_sensors = True
        main.args.disable_system = True
        main.args.disable_wifi = True

        self.stats = GlancesStats(main.config, main.args)

    def update(self):
        self.stats.update()
        return self.stats.getAllAsDict()
