from gevent import monkey
monkey.patch_all()
from gevent.pywsgi import WSGIServer

from flask import Flask, request
import argparse
import json
import logging

import bin.workshop_manager
from bin.server_monitor import *

app = Flask(__name__)
mgr = None


@app.route('/start', methods=['GET', 'POST'])
def start_unit():
	"""Attempts to start a workshop unit on the server node. If an available unit (saved state) 
	is not found, a new unit will be cloned from the template.

    Web service routine:
        /start

    Args:
        workshop (str): The name of the workshop.
        state (str): The resulting state of the unit (run, save).

    Returns:
        A JSON string containing the name of each machine in the unit and their respective VRDE port.
    """
	workshop_name = request.args.get("workshop")
	if workshop_name is None:
		logging.error("Error starting unit: no workshop name provided.")
		return

	state = request.args.get("state")
	if state is None:
		state = "run"

	# Check for available unit
	unit = mgr.find_available_unit(workshop_name)
	if unit is None:
		unit = mgr.clone_wsu(workshop_name)

	mgr.start_wsu(unit)

	# Build JSON for return
	ret = {}
	machines = mgr.vbox.get_machines_by_groups([unit,])
	for machine in machines:
		machine_nat_engine = machine.get_network_adapter(0).nat_engine
		redirects = machine_nat_engine.redirects

		if len(redirects) > 0:
			redirect_items = redirects[1].split(',')
			upstream_id = workshop_name + "_VPN"
			ret[upstream_id] = redirect_items[3]
			machine_nat_engine.remove_redirect(redirect_items[0])

		if machine.vrde_server.enabled:
			port = machine.vrde_server.get_vrde_property('TCP/Ports')
			extension = machine.name.find("WSU")
			upstream_id = workshop_name + "_" + machine.name[extension:]
			ret[upstream_id] = port

	if state == "save":	
		mgr.save_wsu(unit)

	return json.dumps(ret)


@app.route('/stop', methods=['GET', 'POST'])
def stop_unit():
	"""Attempts to stop the workshop unit and remove the virtual machines from VirtualBox 
	depending on the boolean string 'remove'.

    Web service routine:
        /stop

    Args:
        unit (str): Name of the workshop unit to stop.
        remove (str): True to remove, False to restore.

    Returns:
        A string indicating SUCCESS or FAILURE of the request.
    """
	unit = request.args.get("unit")
	if unit is None:
		logging.error("Error stopping unit: no name provided.")
		return
	split = unit.find("WSU")
	workshop_name = unit[0:split-1]
	extension = unit[split:]
	unit_path = "/" + workshop_name + "-Units/" + extension

	remove = request.args.get("remove")
	if remove is None:
		remove = 'True'

	try:
		mgr.stop_wsu(unit_path)
		if remove == 'True':
			mgr.delete_wsu(unit_path)
		else:
			mgr.restore_wsu(unit_path)
	except Exception:
		logging.error("Error stopping unit: " + unit_path)
		return "FAILURE"

	return "SUCCESS"


@app.route('/list', methods=['GET', 'POST'])
def get_workshop_list():
	"""Provides a list of all workshop names available on the server node.

    Web service routine:
        /list

    Args:
        
    Returns:
        A JSON string containing a list of workshop names.
    """
	workshops = []

	for group in mgr.vbox.machine_groups:
		idx = group.find("-Template")
		if idx > 0:	
			workshops.append(group[1:idx])

	return json.dumps(workshops)

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
@app.route('/vbox_stats', methods=['GET', 'POST'])
def vbox_stats():
	return json.dumps(mgr.get_vbox_stats())

'''
{'cpu': 13.9,
 'disk': {'free': 384349720576,
          'percent': 22.3,
          'total': 494864965632,
          'used': 110515245056},
 'virtual-memory': {'available': 10921476096,
                    'free': 10921476096,
                    'percent': 35.9,
                    'total': 17038475264,
                    'used': 6116999168}}
'''
@app.route('/server_stats', methods=['GET', 'POST'])
def server_stats():
	return json.dumps(get_server_stats())


if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)

	# initiate the parser
	parser = argparse.ArgumentParser()  
	parser.add_argument("-I", "--import-workshops", help="Import workshop appliances", action="store_true")

	# read arguments from the command line
	args = parser.parse_args()

	with bin.workshop_manager.WSUManager() as manager:
		mgr = manager

		if args.import_workshops:
			mgr.import_templates()
		
		server = WSGIServer(('0.0.0.0', 5000), app)
		server.serve_forever()
