from __future__ import absolute_import
import ConfigParser
import sys
import os

def parse_config(path):
    """ TODO """
    parser = ConfigParser.SafeConfigParser()
    parser.read(path)
    return dict((s, dict(parser.items(s))) for s in parser.sections())

if "pytest" in sys.modules:
	path = os.path.join('tests', 'config.ini')
else:
	path = 'config.ini'

config = parse_config(path)