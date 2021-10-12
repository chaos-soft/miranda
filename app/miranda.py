#!/usr/bin/env python3
from typing import Any, Union
import atexit
import signal
import sys

from common import WebDriver
from config import CONFIG
from server import Server

TASKS: list[Union[Server, WebDriver]] = []


def main() -> None:
    TASKS.append(Server())
    if 'goodgame' in CONFIG:
        import goodgame
        atexit.register(goodgame.close_driver)
        TASKS.append(goodgame.Chat(CONFIG['goodgame'].get('url')))
        TASKS.append(goodgame.Viewers(CONFIG['goodgame'].get('url')))
        if CONFIG['goodgame'].getboolean('is_play'):
            TASKS.append(goodgame.Play(CONFIG['goodgame'].get('url')))
    if 'sc2tv' in CONFIG:
        import sc2tv
        TASKS.append(sc2tv.Chat(CONFIG['sc2tv'].get('url')))
    if 'twitch' in CONFIG:
        import twitch
        atexit.register(twitch.close_driver)
        TASKS.append(twitch.Chat(CONFIG['twitch'].get('url')))
        TASKS.append(twitch.Viewers(CONFIG['twitch'].get('url')))
        if CONFIG['twitch'].getboolean('is_play'):
            TASKS.append(twitch.Play(CONFIG['twitch'].get('url')))
    if 'wasd' in CONFIG:
        import wasd
        atexit.register(wasd.close_driver)
        TASKS.append(wasd.Chat(CONFIG['wasd'].get('url')))
        TASKS.append(wasd.Viewers(CONFIG['wasd'].get('url')))
        if CONFIG['wasd'].getboolean('is_play'):
            TASKS.append(wasd.Play(CONFIG['wasd'].get('url')))
    for task in TASKS:
        task.start()


def shutdown(*args: Any) -> None:
    print('')
    for task in TASKS[::-1]:
        task.stop()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, shutdown)
    main()
    sys.exit(0)
