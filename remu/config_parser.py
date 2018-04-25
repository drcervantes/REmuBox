import xml.etree.ElementTree as ET
import os
import logging

workshop_fields = [
	"name",
	"appliance"
]

vm_fields = [
	"name",
	"vrdp-enabled",
	"port-forwarding-enabled"
]

def get_templates():
	workshops = []
	for d in os.listdir("templates"):
		config_path = os.path.join(os.getcwd(), "templates", d, "config.xml")
		workshop = get_workshop_config(config_path)
		workshop["appliance"] = os.path.join(os.getcwd(), "templates", d, workshop["appliance"])
		workshops.append(workshop)
	return workshops

def get_workshop_config(config_file):
	workshop = {}

	tree = ET.parse(config_file)
	root = tree.getroot().find("workshop-settings")

	for field in workshop_fields:
		workshop[field] = root.find(field).text.rstrip().lstrip()

	vms = []
	for vm in root.findall("vm"):
		vm_settings = ()
		for field in vm_fields:
			vm_settings += (vm.find(field).text.rstrip().lstrip(),)
		vms.append(vm_settings)

	workshop["vms"] = vms
	return workshop
