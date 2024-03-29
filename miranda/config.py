from configparser import ConfigParser
from pathlib import Path

from . import common


def get_config_file(name) -> Path:
    return Path.home() / '.config' / 'miranda' / name


CONFIG: ConfigParser = ConfigParser(converters={'list': common.str_to_list})
CONFIG.read(get_config_file('config.ini'))
