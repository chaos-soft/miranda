from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any
import asyncio
import collections
import html
import json

import httpx

D = dict[str, Any]
EXCLUDE_IDS: list[str] = ['m']
STATS: dict[str, int | str] = {}
T = list[asyncio.Task]
TIMEOUT_5S: int = 5


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
    sleep: float = 30.0,
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


def dump_credentials(name: str, credentials: D) -> None:
    with get_config_file(name).open('w') as f:
        json.dump(credentials, f)


def get_config_file(name: str) -> Path:
    return Path.home() / '.config' / 'miranda' / name


def load_credentials(name: str) -> D:
    try:
        with open(get_config_file(name)) as f:
            return json.load(f)
    except FileNotFoundError:
        credentials: D = {}
        dump_credentials(name, credentials)
        return credentials


def start_after(variables: str | list[str], globals_: D) -> Callable:
    if type(variables) is str:
        variables = [variables]

    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            for variable in variables:
                while True:
                    v = globals_[variable]
                    if not v:
                        await asyncio.sleep(TIMEOUT_5S)
                    else:
                        break
            return await f(*args, **kwargs)
        return wrapper
    return decorator


def str_to_list(str_: str) -> list[str]:
    """Парсит строку с запятыми в массив."""
    return list(map(str.strip, str_.split(',')))


MESSAGES: UserList = UserList()
