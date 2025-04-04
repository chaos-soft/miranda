from typing import Any
import asyncio
import signal
import sys

from . import commands
from . import server
from .config import CONFIG

TASKS: list[asyncio.Task[None]] = []


async def run() -> None:
    if 'vkplay_playwright' in CONFIG or 'youtube_playwright' in CONFIG:
        from playwright.async_api import async_playwright
        playwright = await async_playwright().start()
        browser = await playwright.firefox.launch(headless=True)
        context = await browser.new_context()
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
            if 'vkplay_playwright' in CONFIG:
                from . import vkplay_playwright
                channel = CONFIG['vkplay_playwright'].get('channel')
                TASKS.append(tg.create_task(vkplay_playwright.VKPlay(channel).main(context)))
            if 'youtube' in CONFIG:
                from . import youtube
                TASKS.append(tg.create_task(youtube.get_authorization_url()))
                TASKS.append(tg.create_task(youtube.get_credentials()))
                TASKS.append(tg.create_task(youtube.refresh_credentials()))
                TASKS.append(tg.create_task(youtube.YouTube().main()))
            if 'youtube_playwright' in CONFIG:
                from . import youtube_playwright
                channel = CONFIG['youtube_playwright'].get('channel')
                id = CONFIG['youtube_playwright'].get('id')
                TASKS.append(tg.create_task(youtube_playwright.YouTube(id).main(context)))
                TASKS.append(tg.create_task(youtube_playwright.YouTubeStats(channel).main(id)))
    except* commands.CommandsError:
        pass
    finally:
        if 'vkplay_playwright' in CONFIG or 'youtube_playwright' in CONFIG:
            await browser.close()
            await playwright.stop()


def main() -> int:
    signal.signal(signal.SIGINT, shutdown)
    asyncio.run(run())
    return 128 + 2


def shutdown(*args: Any) -> None:
    for task in TASKS:
        task.cancel()


sys.exit(main())
