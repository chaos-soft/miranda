from datetime import datetime
from typing import Any, Dict, List
import asyncio
import collections
import html

import aiohttp

D = Dict[str, str]
EXCLUDE_IDS: List[str] = ['m']
TIMEOUT_STATS: int = 60


class UserList(collections.UserList[D]):
    """Список с кастомизированным append().

    Метод применяет html.escape к message['text'],
    если message['id'] не в EXCLUDE_IDS.

    """

    def append(self, message: D) -> None:
        if message['id'] not in EXCLUDE_IDS:
            message['text'] = html.escape(message['text'], quote=True)
        super().append(message)


async def make_request(
    url: str,
    retries: int = 1,
    method: str = 'GET',
    sleep: int = 5,
    **kwargs: Any,
) -> Any:
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


async def print_error(e: str) -> None:
    text = f'[{str(datetime.now()).split(".")[0]}] {e}'
    print(text)
    MESSAGES.append(dict(id='m', text=text))


def str_to_list(str_: str) -> List[str]:
    """Парсит строку с запятыми в массив."""
    return list(map(str.strip, str_.split(',')))


MESSAGES: UserList = UserList()
