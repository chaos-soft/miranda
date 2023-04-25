from typing import Any
import asyncio
import signal
import sys

from . import commands
from . import server
from .config import CONFIG

TASKS: list[asyncio.Task[None]] = []


async def run() -> None:
    try:
        async with asyncio.TaskGroup() as tg:
            TASKS.append(tg.create_task(server.Server().main()))
            if 'commands' in CONFIG:
                TASKS.append(tg.create_task(commands.Commands().main()))
            if 'goodgame' in CONFIG:
                from . import goodgame
                for channel in CONFIG['goodgame'].getlist('channels'):
                    g = goodgame.GoodGame(channel)
                    TASKS.append(tg.create_task(g.main()))
                    TASKS.append(tg.create_task(g.send_heartbeat()))
            if 'sc2tv' in CONFIG:
                from . import sc2tv
                for channel in CONFIG['sc2tv'].getlist('channels'):
                    s = sc2tv.Sc2tv(channel)
                    TASKS.append(tg.create_task(s.main()))
                    TASKS.append(tg.create_task(s.send_heartbeat()))
            if 'twitch' in CONFIG:
                from . import twitch
                channels = CONFIG['twitch'].getlist('channels')
                for channel in channels:
                    TASKS.append(tg.create_task(twitch.Twitch(channel).main()))
                    if channels.index(channel) == 0:
                        if CONFIG['twitch'].getboolean('is_follows'):
                            TASKS.append(tg.create_task(twitch.get_channel_id(channel)))
                            TASKS.append(tg.create_task(twitch.TwitchFollows(channel).main()))
                        if CONFIG['twitch'].getboolean('is_stats'):
                            TASKS.append(tg.create_task(twitch.TwitchStats(channel).main()))
    except* commands.CommandsError:
        pass


def main() -> int:
    signal.signal(signal.SIGINT, shutdown)
    asyncio.run(run())
    return 0


def shutdown(*args: Any) -> None:
    for task in TASKS:
        task.cancel()


sys.exit(main())
