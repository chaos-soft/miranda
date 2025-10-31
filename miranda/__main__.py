from collections.abc import Callable
from typing import Any
import asyncio
import importlib
import signal
import sys

from . import commands
from . import server
from .common import T
from .config import CONFIG

MODULES: list[str] = [
    'commands',
    'eww',
    'goodgame',
    'twitch',
    'vkplay',
    'youtube',
    'youtube_playwright',
]
SHUTDOWN: list[Callable] = []
TASKS: T = []


async def run() -> None:
    try:
        async with asyncio.TaskGroup() as tg:
            TASKS.append(tg.create_task(server.Server().main()))
            for module_name in MODULES:
                if module_name in CONFIG:
                    module = importlib.import_module(f'miranda.{module_name}')
                    module.TG = tg  # type: ignore
                    SHUTDOWN.append(module.shutdown)
                    tg.create_task(module.start())
    except* commands.KillError:
        pass
    except* commands.RestartError:
        shutdown()
        await run()


def main() -> int:
    signal.signal(signal.SIGINT, shutdown)
    asyncio.run(run())
    return 128 + 2


def shutdown(*args: Any) -> None:
    for shutdown in SHUTDOWN:
        shutdown()
    for task in TASKS:
        task.cancel()
    SHUTDOWN.clear()
    TASKS.clear()


sys.exit(main())
