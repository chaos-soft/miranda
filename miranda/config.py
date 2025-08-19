from configparser import ConfigParser

from . import common

CONFIG: ConfigParser = ConfigParser(converters={'list': common.str_to_list})
CONFIG.read(common.get_config_file('config.ini'))
