import re
from datetime import datetime
import html
import threading
import time


def print_error(messages, e):
    t = '[{}] {}'.format(str(datetime.now()).split(' ')[1][:8], e)
    print(t)
    messages.append(dict(id='m', text=t))


class Chat(threading.Thread):

    def __init__(self, channel, config, messages, smiles, stop_event):
        super().__init__()
        self.channel = channel
        self.config = config
        self.messages = messages
        self.smiles = smiles
        self.stop_event = stop_event

        self.re_html = re.compile(r'<.*?>')
        self.re_smile = re.compile(r':(\w+):')

        if hasattr(self, 'load_follows') and int(config['base']['follows_limit']):
            self.follows = self.load_follows()
        else:
            self.follows = {}

        self.start()

    def print_error(self, e):
        print_error(self.messages, e)

    def filter(self, name, text):
        """
        Проверяет пользователя на бан. Удаляет HTML и делает экранирование,
        если не root.
        """
        name = name.lower()
        text = self.re_html.sub('', text)
        root = list(map(str.strip, self.config['base']['root'].split(',')))

        if name not in root:
            banned = list(map(str.strip, self.config['base']['banned'].split(',')))
            if name in banned:
                return
            text = html.escape(text, quote=False)

        return text

    def on_error(self, s, e):
        self.print_error('{}: {}'.format(type(self).__name__, e))

    def on_close(self, _):
        self.print_error('{} stopped (@{}).'.format(type(self).__name__, self.channel))

        if not self.stop_event.is_set():
            time.sleep(5)
            self.socket_start()
