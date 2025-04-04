from datetime import datetime
from typing import Any
import asyncio
import collections
import html

import httpx

D = dict[str, Any]
EXCLUDE_IDS: list[str] = ['m']
STATS: dict[str, int | str] = {}


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
    is_json: bool = True,
    **kwargs: Any,
) -> Any:
    while retries:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.request(method, url, **kwargs)
                assert r.status_code == 200
                if is_json:
                    return r.json()
                else:
                    return r.text
        except Exception as e:
            await print_error(f'{type(e).__name__}: {url}')
            retries -= 1
            if retries:
                await asyncio.sleep(sleep)
    return None


async def print_error(e: str) -> None:
    text = f'[{str(datetime.now()).split(".")[0]}] {e}'
    print(text)
    MESSAGES.append(dict(id='m', text=text))


def str_to_list(str_: str) -> list[str]:
    """Парсит строку с запятыми в массив."""
    return list(map(str.strip, str_.split(',')))


MESSAGES: UserList = UserList()
