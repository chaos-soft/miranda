from datetime import datetime
import collections
import html
import time

import requests

EXCLUDE_IDS = ['m']
MESSAGES = None


class UserList(collections.UserList):
    """Список с кастомизированным append().

    Метод применяет html.escape к message['text'],
    если message['id'] не в EXCLUDE_IDS.

    """

    def append(self, message):
        if message['id'] not in EXCLUDE_IDS:
            message['text'] = html.escape(message['text'], quote=True)
        super().append(message)


def print_error(e):
    text = '[{}] {}'.format(str(datetime.now()).split('.')[0], e)
    print(text)
    MESSAGES.append(dict(id='m', text=text))


def str_to_list(str_):
    """Парсит строку с запятыми в массив."""
    return list(map(str.strip, str_.split(',')))


def make_request(url, retries=1, method=requests.get, sleep=5, **kwargs):
    while retries:
        try:
            r = method(url, **kwargs)
            r.raise_for_status()
            data = r.json()
            return data
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            print_error(e)
            retries -= 1
            if retries:
                time.sleep(sleep)
    return None


def timeout_generator(timeout=60, sleep=1):
    while timeout:
        timeout -= sleep
        time.sleep(sleep)
        yield True
    yield False


MESSAGES = UserList()
