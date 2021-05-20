#!/usr/bin/env python3
from typing import Any, List
import asyncio
import signal
import sys

from config import CONFIG
import aiohttp
import server

TASKS: List[asyncio.Task[None]] = []


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        TASKS.append(asyncio.create_task(server.Server().main()))
        if 'twitch' in CONFIG:
            import twitch
            channels = CONFIG['twitch'].getlist('channels')
            for channel in channels:
                TASKS.append(asyncio.create_task(twitch.Twitch(channel).main(session)))
                if channels.index(channel) == 0:
                    if CONFIG['twitch'].getboolean('is_follows'):
                        TASKS.append(asyncio.create_task(twitch.get_channel_id(channel)))
                        TASKS.append(asyncio.create_task(twitch.TwitchFollows(channel).main()))
                    if CONFIG['base'].getboolean('is_stats'):
                        TASKS.append(asyncio.create_task(twitch.TwitchStats(channel).main()))
        if 'goodgame' in CONFIG:
            import goodgame
            for channel in CONFIG['goodgame'].getlist('channels'):
                TASKS.append(asyncio.create_task(goodgame.GoodGame(channel).main(session)))
        if 'peka2tv' in CONFIG:
            import peka2tv
            for channel in CONFIG['peka2tv'].getlist('channels'):
                TASKS.append(asyncio.create_task(peka2tv.Peka2tv(channel).main(session)))
        if 'commands' in CONFIG:
            import commands
            TASKS.append(asyncio.create_task(commands.Commands().main()))
        await asyncio.gather(*TASKS)


def shutdown(*args: Any) -> None:
    for task in TASKS:
        task.cancel()
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, shutdown)
    asyncio.run(main())
