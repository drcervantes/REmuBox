from __future__ import absolute_import
import ConfigParser

def parse_config(path):
    """ TODO """
    parser = ConfigParser.SafeConfigParser()
    parser.read(path)
    return dict((s, dict(parser.items(s))) for s in parser.sections())

config = parse_config('config.ini')