import os
import configparser

import common

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = configparser.ConfigParser(converters={'list': common.str_to_list})
CONFIG.read(os.path.join(BASE_DIR, 'config.ini'))
