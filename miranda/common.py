from abc import ABCMeta
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any
import asyncio
import json

import httpx

D = dict[str, Any]
T = list[asyncio.Task]

STATS: dict[str, int | str] = {}
TIMEOUT_5S: int = 5


class MessageABC(metaclass=ABCMeta):
    id: str
    images: D
    name: str
    text: str

    def __init__(self, **kwargs: Any) -> None:
        self.images = {}
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get(self, k: str, default: Any = None) -> Any:
        return getattr(self, k, default)

    def to_dict(self) -> D:
        return {'id': self.id, 'images': self.images, 'name': self.name, 'text': self.text}


class MessageMiranda(MessageABC):
    id = 'm'
    is_donate: bool = False
    is_event: bool = False
    is_js: bool = False
    is_tts: bool = False
    name = 'Miranda'

    def to_dict(self) -> D:
        d = super().to_dict()
        d['is_donate'] = self.is_donate
        d['is_event'] = self.is_event
        d['is_js'] = self.is_js
        d['is_tts'] = self.is_tts
        return d


async def loop(f: Callable, timeout: int = TIMEOUT_5S) -> None:
    while True:
        await asyncio.sleep(timeout)
        await f()


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
            print_error(f'{type(e).__name__}: {url}')
            retries -= 1
            if retries:
                await asyncio.sleep(sleep)
    return None


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


def messages_to_dict(messages: list[MessageABC]) -> list[dict]:
    return [v if type(v) is dict else v.to_dict() for v in messages]


def print_error(e: str) -> None:
    text = f'[{str(datetime.now()).split(".")[0]}] {e}'
    print(text)
    MESSAGES.append(MessageMiranda(text=text))


def start_after(variables: str | list[str], globals_: D) -> Callable:
    if type(variables) is str:
        variables = [variables]

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        async def wrapper(*args: Any, **kwargs: Any) -> Callable:
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


MESSAGES: list[MessageABC] = []
