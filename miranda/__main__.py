from typing import Any
import asyncio
import signal
import sys

from . import commands
from . import server
from . import twitch
from . import vkplay
from . import youtube_playwright
from .config import CONFIG

TASKS: list[asyncio.Task[None]] = []


async def run() -> None:
    try:
        async with asyncio.TaskGroup() as tg:
            twitch.TG = tg
            vkplay.TG = tg
            youtube_playwright.TG = tg
            TASKS.append(tg.create_task(server.Server().main()))
            TASKS.append(tg.create_task(twitch.start()))
            TASKS.append(tg.create_task(vkplay.start()))
            TASKS.append(tg.create_task(youtube_playwright.start()))

            if 'commands' in CONFIG:
                TASKS.append(tg.create_task(commands.Commands().main()))

            if 'goodgame' in CONFIG:
                from . import goodgame
                for channel in CONFIG['goodgame'].getlist('channels'):
                    g = goodgame.GoodGame(channel)
                    TASKS.append(tg.create_task(g.main()))
                    TASKS.append(tg.create_task(g.send_heartbeat()))

            if 'youtube' in CONFIG:
                from . import youtube
                TASKS.append(tg.create_task(youtube.get_authorization_url()))
                TASKS.append(tg.create_task(youtube.get_credentials()))
                TASKS.append(tg.create_task(youtube.refresh_credentials()))
                TASKS.append(tg.create_task(youtube.YouTube().main()))
    except* commands.CommandsError:
        pass


def main() -> int:
    signal.signal(signal.SIGINT, shutdown)
    asyncio.run(run())
    return 128 + 2


def shutdown(*args: Any) -> None:
    twitch.shutdown()
    vkplay.shutdown()
    youtube_playwright.shutdown()
    for task in TASKS:
        task.cancel()


sys.exit(main())
