import re
import threading
from datetime import datetime
import time

from common import print_error


class Commands(threading.Thread):
    start_timestamp = datetime.now().timestamp()

    def __init__(self, config, messages, stop_event):
        super().__init__()

        self.config = config
        self.messages = messages
        self.stop_event = stop_event
        self.text = config['base'].getlist('text')
        self.exclude_ids = config['base'].getlist('exclude_ids')
        self.include_ids = config['commands'].getlist('include_ids')

        self.commands = {}
        for k in config['commands']:
            if k.startswith('-'):
                self.commands[k] = config['commands'].getlist(k)

        self.re_commands_keys = re.compile(r'({})(.*)'. \
            format('|'.join(self.commands.keys())))

        self.start()

    def run(self):
        print_error(self.messages, '{} loaded.'.format(type(self).__name__))
        offset = 0

        while not self.stop_event.is_set():
            for message in self.messages[offset:]:
                if message['id'] in self.exclude_ids:
                    continue

                m = self.re_commands_keys.search(message['text'])
                if not m:
                    continue

                # Параметры команды.
                # p = ['имя метода', 'владелец', 'время с подписки']
                p = self.commands[m.group(1)]

                is_command = False
                try:
                    t = message.get('timestamp', self.start_timestamp)
                    # Проверка времени с подписки.
                    if self.start_timestamp - t >= int(p[2]):
                        is_command = True
                except IndexError:
                    is_command = True

                # Может ли пользователь использовать команду.
                if message.get('is_muted'):
                    pass
                elif message.get('is_root') or \
                     message['id'] in self.include_ids or \
                     (p[1] == 'follows' and message.get('is_friendly')) or \
                     p[1] == '*' or \
                     (p[1] == 'follows' and is_command):
                    getattr(self, p[0])(message=message, command_text=m.group(2).strip())

            offset += len(self.messages) - offset
            time.sleep(0.5)

    def say_hi(self, message, **kwargs):
        self.add_tts(self.text[2].format(message['name']))

    def add_tts(self, command_text, **kwargs):
        if command_text:
            self.add_js('tts.push("{}")'.format(command_text[:300]))

    def add_image(self, message, command_text):
        if command_text:
            if 'replacements' not in message:
                message['replacements'] = {}
            message['replacements'][command_text] = command_text

    def add_js(self, command_text, **kwargs):
        self.messages.append(dict(id='js', command=command_text))

    def clean_chat(self, **kwargs):
        self.add_js('main.clean()')

    def stop(self):
        self.join()
        print_error(self.messages, '{} stopped.'.format(type(self).__name__))

    def print_to_console(self, command_text, **kwargs):
        print(command_text) if command_text else None

    def mute_user(self, command_text, **kwargs):
        muted = self.config['base'].getlist('muted')
        muted.append(command_text)
        self.config['base']['muted'] = ', '.join(muted)

    def unmute_user(self, command_text, **kwargs):
        muted = self.config['base'].getlist('muted')
        muted.remove(command_text)
        self.config['base']['muted'] = ', '.join(muted)

    def clean_messages(self, **kwargs):
        self.messages[:] = []
