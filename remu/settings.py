import configparser

def parse_config(path):
    """ TODO """
    parser = configparser.ConfigParser()
    parser.read(path)
    return {s:dict(parser.items(s)) for s in parser.sections()}

config = parse_config('config.ini')