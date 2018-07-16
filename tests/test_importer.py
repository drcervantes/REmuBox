import pytest
import os

from remu.server import WorkshopManager

@pytest.mark.importer
@pytest.mark.usefixtures('importer')
class TestImporter():
	def test_parse_config_normal(self):
		path = os.path.join(self.importer.path, 'Test_Workshop', 'config.xml')
		config = self.importer._parse_config(path)
		assert config['name'] == 'Test_Workshop'
		assert len(config['appliance']) > 0
		assert len(config['vms']) > 0

	def test_parse_config_no_file(self):
		with pytest.raises(Exception):
			self.importer._parse_config('fake')


	def test_get_templates_normal(self):
		templates = self.importer.get_templates()
		assert len(templates) > 0
		assert os.path.exists(templates[0]['appliance'][0])

	def test_get_templates_no_dir(self):
		path = self.importer.path
		self.importer.path = 'fake'

		with pytest.raises(Exception):
			self.importer.get_templates()

		self.importer.path = path
		assert self.importer.path == path


	def test_import_template_normal(self):
		templates = self.importer.get_templates()
		self.importer._import_template(templates[0])

		assert '/Test_Workshop-Template' in self.importer.vbox.machine_groups

		for m in self.importer.vbox.get_machines_by_groups(['/Test_Workshop-Template']):
			WorkshopManager._delete_machine(m)