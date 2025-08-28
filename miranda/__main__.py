from collections.abc import Callable
from typing import Any
import asyncio
import signal
import sys

from . import commands
from . import server
from .common import T
from .config import CONFIG

SHUTDOWN: list[Callable] = []
TASKS: T = []


async def run() -> None:
    try:
        async with asyncio.TaskGroup() as tg:
            TASKS.append(tg.create_task(server.Server().main()))
            if 'commands' in CONFIG:
                TASKS.append(tg.create_task(commands.Commands().main()))

            if 'goodgame' in CONFIG:
                from . import goodgame
                goodgame.TG = tg
                SHUTDOWN.append(goodgame.shutdown)
                TASKS.append(tg.create_task(goodgame.start()))

            if 'twitch' in CONFIG:
                from . import twitch
                twitch.TG = tg
                SHUTDOWN.append(twitch.shutdown)
                TASKS.append(tg.create_task(twitch.start()))

            if 'vkplay' in CONFIG:
                from . import vkplay
                vkplay.TG = tg
                SHUTDOWN.append(vkplay.shutdown)
                TASKS.append(tg.create_task(vkplay.start()))

            if 'youtube' in CONFIG:
                from . import youtube
                youtube.TG = tg
                SHUTDOWN.append(youtube.shutdown)
                TASKS.append(tg.create_task(youtube.start()))

            if 'youtube_playwright' in CONFIG:
                from . import youtube_playwright
                youtube_playwright.TG = tg
                SHUTDOWN.append(youtube_playwright.shutdown)
                TASKS.append(tg.create_task(youtube_playwright.start()))
    except* commands.CommandsError:
        pass


def main() -> int:
    signal.signal(signal.SIGINT, shutdown)
    asyncio.run(run())
    return 128 + 2


def shutdown(*args: Any) -> None:
    for shutdown in SHUTDOWN:
        shutdown()
    for task in TASKS:
        task.cancel()


sys.exit(main())
