from configparser import ConfigParser

from . import common

file_path = common.get_config_file('config.ini')
if not file_path.exists():
    raise FileNotFoundError(file_path)
CONFIG: ConfigParser = ConfigParser(converters={'list': common.str_to_list})
CONFIG.read(file_path)
