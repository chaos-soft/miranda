from datetime import datetime
import collections
import html
import asyncio

import aiohttp

EXCLUDE_IDS = ['m']


class UserList(collections.UserList):
    """Список с кастомизированным append().

    Метод применяет html.escape к message['text'],
    если message['id'] не в EXCLUDE_IDS.

    """

    def append(self, message):
        if message['id'] not in EXCLUDE_IDS:
            message['text'] = html.escape(message['text'], quote=True)
        super().append(message)


async def make_request(url, retries=1, method='GET', sleep=5, **kwargs):
    while retries:
        try:
            async with aiohttp.request(method, url, **kwargs) as r:
                assert r.status == 200
                return await r.json()
        except AssertionError:
            await print_error(f'AssertionError: {url} ({r.status})')
            retries -= 1
            if retries:
                await asyncio.sleep(sleep)
    return None


async def print_error(e):
    text = f'[{str(datetime.now()).split(".")[0]}] {e}'
    print(text)
    MESSAGES.append(dict(id='m', text=text))


def str_to_list(str_):
    """Парсит строку с запятыми в массив."""
    return list(map(str.strip, str_.split(',')))


MESSAGES = UserList()
