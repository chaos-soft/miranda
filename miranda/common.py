from abc import ABCMeta
from collections.abc import Callable
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import Any
import asyncio
import collections
import importlib
import json
import logging.config

import httpx  # type: ignore

D = dict[str, Any]
T = list[asyncio.Task]

MESSAGES_EVENT: asyncio.Event = asyncio.Event()
RESTART_EVENT: asyncio.Event = asyncio.Event()
SHUTDOWN_EVENT: asyncio.Event = asyncio.Event()
STATS: dict[str, int | str] = {}
TIMEOUT_5S: int = 5


def get_config_file(name: str) -> Path:
    return Path.home() / ".config" / "miranda" / name


with open(get_config_file("config_logging.json")) as f:
    logging.config.dictConfig(json.load(f))
logger: logging.Logger = logging.getLogger("miranda")


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
        return {
            "id": self.id,
            "images": self.images,
            "name": self.name,
            "text": self.text,
        }


class MessageMiranda(MessageABC):
    id = "m"
    is_donate: bool = False
    is_event: bool = False
    is_js: bool = False
    is_tts: bool = False
    name = "Miranda"

    def to_dict(self) -> D:
        d = super().to_dict()
        d["is_donate"] = self.is_donate
        d["is_event"] = self.is_event
        d["is_js"] = self.is_js
        d["is_tts"] = self.is_tts
        return d


class Module:
    is_active: bool
    module: Any
    name: str

    def __init__(self, name: str):
        self.is_active = True
        self.module = importlib.import_module(f"miranda.{name}")
        self.name = name

    def activate(self):
        self.is_active = True
        RESTART_EVENT.set()

    def deactivate(self):
        self.is_active = False
        RESTART_EVENT.set()

    def start(self):
        if self.is_active:
            asyncio.create_task(self.module.start())


class Singleton(type):
    instances: dict[type, Any] = {}

    def __call__(cls) -> Any:
        if cls not in cls.instances:
            cls.instances[cls] = super().__call__()
        return cls.instances[cls]


class UserList(collections.UserList[MessageABC]):
    commands: Any = None

    def append(self, message: MessageABC) -> None:
        MESSAGES_EVENT.set()
        super().append(message)
        if not self.commands:
            self.init_commands()
        self.commands.main(message)

    def init_commands(self):
        module = importlib.import_module("miranda.commands")
        self.commands = module.Commands()


class ModuleManager(metaclass=Singleton):
    modules: dict[str, Module]

    def __init__(self):
        self.modules = {}

    def activate_module(self, name: str):
        if name in self.modules:
            self.modules[name].activate()

    def deactivate_module(self, name: str):
        if name in self.modules:
            self.modules[name].deactivate()

    def init_modules(self, config: ConfigParser, modules: list[str]):
        for name in modules:
            if name in config:
                if name not in self.modules:
                    self.modules[name] = Module(name)
            else:
                self.modules.pop(name, None)

    def start(self):
        for name, module in self.modules.items():
            module.start()


async def loop(f: Callable, timeout: int = TIMEOUT_5S) -> None:
    while True:
        await asyncio.sleep(timeout)
        await f()


async def make_request(
    url: str,
    method: str = "GET",
    timeout: int = 60,
    is_json: bool = True,
    **kwargs: Any,
) -> Any:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.request(method, url, timeout=timeout, **kwargs)
            assert r.status_code == 200
            if is_json:
                return r.json()
            else:
                return r.text
    except Exception as e:
        print_error(f"{type(e).__name__}: {url}")
        return None


def messages_to_dict(messages: list[MessageABC]) -> list[dict]:
    return [v if type(v) is dict else v.to_dict() for v in messages]


def print_error(e: str) -> None:
    text = "[{}] {}".format(str(datetime.now()).split(".")[0], e)
    logger.info(e)
    MESSAGES.append(MessageMiranda(text=text))


def str_to_list(str_: str) -> list[str]:
    """Парсит строку с запятыми в массив."""
    return list(map(str.strip, str_.split(",")))


MESSAGES: UserList = UserList()
