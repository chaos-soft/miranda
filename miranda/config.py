from configparser import ConfigParser

from . import common


def load() -> None:
    CONFIG.read(common.get_config_file('config.ini'))


file_path = common.get_config_file('config.ini')
if not file_path.exists():
    raise FileNotFoundError(file_path)
CONFIG: ConfigParser = ConfigParser(converters={'list': common.str_to_list})
load()
