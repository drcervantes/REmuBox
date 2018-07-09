from __future__ import print_function

import xml.etree.ElementTree as et
import os
import sys
import logging
import subprocess
import virtualbox

from remu.settings import config

l = logging.getLogger(config["REMU"]["logger"])

"""
TODO: vrde port is checked by the machine configuration and not the xml
"""
class Templates():
    def __init__(self, vbox=None):
        self.vbox = vbox
        self.path = config['REMU']['workshops']

    def __enter__(self):
        if not self.vbox:
            self.vbox = virtualbox.VirtualBox()
        return self

    def __exit__(self, *args):
        del self.vbox

    def _parse_config(self, config_file):
        tree = et.parse(config_file)
        root = tree.getroot().find("workshop-settings")

        # Create a dictionary of all elements in the root
        workshop = {child.tag:child.text.strip() for child in root.getchildren() if not bool(child.getchildren())}
        workshop["appliance"] = [child.text.strip() for child in root.findall("appliance")]

        # Create a list of dictionaries containing the elements within the vm tag
        vms = [{child.tag:child.text.strip() for child in vm.getchildren()} for vm in root.findall("vm")]
        workshop["vms"] = vms

        return workshop

    def get_templates(self):
        workshops = []

        for workshop_dir in os.listdir(self.path):
            config_path = os.path.join(self.path, workshop_dir, "config.xml")
            workshop = self._parse_config(config_path)

            # Get the full path of the appliance for importing later
            workshop["appliance"] = [os.path.join(self.path, workshop_dir, app) for app in workshop["appliance"]]
            workshops.append(workshop)

        return workshops

    def _progress_bar(self, progress):
        try:
            while not progress.completed:
                print("Completion: %s %%\r" % str(progress.percent), end="")
                sys.stdout.flush()
                progress.wait_for_completion(int(config['REMU']['timeout']))

        except KeyboardInterrupt:
            l.error("Interrupted.")
            if progress.cancelable:
                l.error("Cancelling task...")
                progress.cancel()

    def _import_template(self, template):
        l.info("Importing template: %s", template["name"])
        
        try:
            for app in template["appliance"]:
                appliance = self.vbox.create_appliance()
                l.debug(" ... reading: %s", str(app))
                appliance.read(app)

                progress = appliance.import_machines()
                self._progress_bar(progress)

                for machine_id in appliance.machines:
                    machine = self.vbox.find_machine(machine_id)
                    l.info(" ... importing machine: %s", machine.name)

                    group = "/" + template["name"] + "-Template"
                    dummy = subprocess.check_output([config['REMU']['vbox_manage'], "modifyvm", machine.name, "--groups", group])
                    session = machine.create_session()
                    progress, dummy = session.machine.take_snapshot(
                        'Original',
                        'Snapshot of the original state of the machine used for creating/restoring cloned units.',
                        False
                    )
                    progress.wait_for_completion()
                    session.unlock_machine()
            l.info("%s imported successfully", template["name"])
        except Exception:
            l.exception("Failed to import %s template!", template["name"])

    def import_new(self):
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

        templates = [t for t in self.get_templates() if t["name"] not in existing_templates]

        for t in templates:
            self._import_template(t)
