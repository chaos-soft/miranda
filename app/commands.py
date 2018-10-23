from datetime import datetime
import time

from common import MESSAGES, EXCLUDE_IDS
from config import CONFIG
from chat import Base

EXCLUDE_IDS.extend(['js', 'tts'])
INCLUDE_IDS = ['p', 'e']


class Commands(Base):
    offset = 0
    start_timestamp = datetime.now().timestamp()
    root = CONFIG['base'].getlist('root')
    friendly = CONFIG['base'].getlist('friendly')

    def run(self):
        self.on_start()
        commands = {}
        for k in CONFIG['commands']:
            commands[k] = CONFIG['commands'].getlist(k)
        while not self.is_stop:
            for message in MESSAGES[self.offset:]:
                self.offset += 1
                if message['id'] in EXCLUDE_IDS:
                    continue
                # Параметры команды.
                # p = ['имя метода', 'владелец', 'время с подписки']
                for k, p in commands.items():
                    if message['text'].startswith(k):
                        break
                else:
                    continue
                self.add_role(message)
                # Может ли пользователь использовать команду.
                if (message.get('is_root') or
                        message['id'] in INCLUDE_IDS or
                        (p[1] == 'follows' and message.get('is_friendly')) or
                        p[1] == '*' or
                        (p[1] == 'follows' and self.is_timestamp(message, p))):
                    getattr(self, p[0])(
                        message=message,
                        command_text=message['text'][len(k):].strip())
            time.sleep(0.5)

    def stop(self):
        self.on_close()
        super().stop()

    def is_timestamp(self, message, params):
        is_timestamp = False
        try:
            timestamp = message.get('timestamp', self.start_timestamp)
            # Проверка времени с подписки.
            if self.start_timestamp - timestamp >= int(params[2]):
                is_timestamp = True
        except IndexError:
            is_timestamp = True
        return is_timestamp

    def add_role(self, message):
        name = message['name'].lower()
        if name in self.root:
            message['is_root'] = True
        elif name in self.friendly:
            message['is_friendly'] = True

    def add_tts(self, message, command_text):
        if command_text:
            MESSAGES.append(dict(id='tts', text=command_text[:300]))

    def add_image(self, message, command_text):
        if command_text:
            if 'replacements' not in message:
                message['replacements'] = []
            message['replacements'].append(command_text)

    def clean_chat(self, **kwargs):
        MESSAGES.append(dict(id='js', text='clean_chat'))

    def print_to_console(self, message, command_text):
        if command_text:
            print(command_text)

    def clean_messages(self, **kwargs):
        MESSAGES[:] = []
        self.offset = 0
        self.clean_chat()
