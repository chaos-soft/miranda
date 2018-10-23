import threading
import time

from common import print_error


class Base(threading.Thread):
    is_stop = False

    def __init__(self):
        super().__init__()
        self.start()

    def stop(self):
        self.join()

    def print_error(self, pattern, *args):
        name = type(self).__name__
        if hasattr(self, 'channel') and self.channel:
            name = '{} (@{})'.format(name, self.channel)
        print_error(pattern.format(name, *args))

    def on_error(self, *args):
        self.print_error('{}: {}', args[-1])

    def on_close(self):
        self.print_error('{} остановлен.')

    def on_start(self):
        self.print_error('{} запущен.')


class Chat(Base):

    def __init__(self, channel=None):
        self.channel = channel
        super().__init__()

    def start_socket(self):
        raise NotImplementedError

    def on_close(self, socket=None):
        super().on_close()
        if socket:
            socket.close()
        if not self.is_stop:
            time.sleep(5)
            self.start_socket()
