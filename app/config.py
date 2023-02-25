from configparser import ConfigParser
import os

import common

BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))

CONFIG: ConfigParser = ConfigParser(converters={'list': common.str_to_list})
CONFIG.read(os.path.join(BASE_DIR, 'config.ini'))
