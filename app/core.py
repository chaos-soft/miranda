#!/usr/bin/env python3
import time
import sys
import signal

import server
from config import CONFIG


class ShutdownError(Exception):
    pass


def shutdown(signum, frame):
    raise ShutdownError


def main():
    signal.signal(signal.SIGINT, shutdown)
    try:
        server_thread = server.Server()
        threads = []
        if 'twitch' in CONFIG:
            import twitch
            channels = CONFIG['twitch'].getlist('channels')
            for channel in channels:
                threads.append(twitch.Twitch(channel))
                if channels.index(channel) == 0:
                    if CONFIG['twitch'].getboolean('is_follows'):
                        threads.append(twitch.TwitchFollows(channel))
                    if CONFIG['twitch'].getboolean('is_hosts'):
                        threads.append(twitch.TwitchHosts(channel))
        if 'goodgame' in CONFIG:
            import goodgame
            for channel in CONFIG['goodgame'].getlist('channels'):
                threads.append(goodgame.GoodGame(channel))
        if 'peka2tv' in CONFIG:
            import peka2tv
            for channel in CONFIG['peka2tv'].getlist('channels'):
                threads.append(peka2tv.Peka2tv(channel))
        if CONFIG['base'].getboolean('is_youtube'):
            import youtube
            threads.append(youtube.YouTube())
            threads.append(youtube.YouTubeAuthorization())
        if 'commands' in CONFIG:
            import commands
            threads.append(commands.Commands())
        while True:
            time.sleep(5)
    except ShutdownError:
        for thread in threads:
            thread.is_stop = True
            thread.stop()
        server_thread.stop()
        sys.exit(0)


if __name__ == '__main__':
    main()
