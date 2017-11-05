import re
import html
import threading
import time

from common import print_error


class Chat(threading.Thread):

    def __init__(self, channel, config, messages, smiles, stop_event, *args):
        super().__init__()

        self.channel = channel
        self.config = config
        self.messages = messages
        self.smiles = smiles
        self.stop_event = stop_event
        self.re_smile = re.compile(r':(\w+):')
        self.root = config['base'].getlist('root')
        self.friendly = config['base'].getlist('friendly')

        if hasattr(self, 'load_follows') and config['base'].getint('follows_limit'):
            self.follows = self.load_follows()
        else:
            self.follows = {}

        self.start()

    def print_error(self, e):
        print_error(self.messages, e)

    def add_role(self, message):
        """
        Добавляет роль пользователя к сообщению (is_root, is_muted или is_friendly).
        """
        name = message['name'].lower()

        if name in self.root:
            message['is_root'] = True
        else:
            if name in self.config['base'].getlist('muted'):
                message['is_muted'] = True
            elif name in self.friendly:
                message['is_friendly'] = True

    def on_error(self, *args):
        self.print_error('{}: {}'.format(type(self).__name__, args[-1]))

    def on_close(self, *args):
        if self.channel:
            t = '{} stopped (@{}).'.format(type(self).__name__, self.channel)
        else:
            t = '{} stopped.'.format(type(self).__name__)
        self.print_error(t)

        if not self.stop_event.is_set():
            time.sleep(5)
            self.socket_start()
