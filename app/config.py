from configparser import ConfigParser
import os


def str_to_list(str_: str) -> list[str]:
    """Парсит строку с запятыми в массив."""
    return list(filter(None, map(str.strip, str_.split(','))))


BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
CONFIG: ConfigParser = ConfigParser(converters={'list': str_to_list})

CONFIG.read(os.path.join(BASE_DIR, 'config.ini'))
