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
                if message.get('is_root') or \
                   message['id'] in INCLUDE_IDS or \
                   (p[1] == 'follows' and message.get('is_friendly')) or \
                   p[1] == '*' or \
                   (p[1] == 'follows' and self.is_timestamp(message, p)):
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

    def add_test_messages(self, **kwargs):
        self.add_test_messages_t()
        self.add_test_messages_g()
        self.add_test_messages_s()
        self.add_test_messages_y()
        self.add_test_messages_p()

    def add_test_messages_t(self):
        message = dict(id='t', name='chaos_soft', color='#ff69b4')
        message['text'] = '-i https://gals.kindgirls.com/d3/ariel_39844/m6/ariel_39844_1.jpg'
        MESSAGES.append(message.copy())
        message['text'] = '-t от root'
        MESSAGES.append(message.copy())
        message['text'] = '<3 <3 <3 <3 xxx <3 <3 <3 <3'
        message['emotes'] = '9:0-1,3-4,6-7,9-10,16-17,19-20,22-23,25-26'
        MESSAGES.append(message.copy())
        message['text'] = 'LUL ResidentSleeper SeriousSloth'
        message['emotes'] = '425618:0-2/245:4-18/81249:20-31'
        MESSAGES.append(message.copy())

    def add_test_messages_g(self):
        message = dict(id='g', name='chaos-soft')
        message['text'] = '-i https://gals.kindgirls.com/d3/ariel_09328/m6/ariel_09328_2.jpg'
        MESSAGES.append(message.copy())
        message['text'] = '-t от friendly'
        MESSAGES.append(message.copy())
        message['text'] = ':peka: :gta: :bearbush:'
        MESSAGES.append(message.copy())

    def add_test_messages_s(self):
        message = dict(id='s', name='xxx')
        message['text'] = '-i https://gals.kindgirls.com/d3/ariel_09328/m6/ariel_09328_8.jpg'
        MESSAGES.append(message.copy())
        message['text'] = '-t от xxx'
        MESSAGES.append(message.copy())
        message['text'] = '@chaos обращение'
        MESSAGES.append(message.copy())
        message['text'] = ':frog: :uuu: :rainbowfrog:'
        MESSAGES.append(message.copy())

    def add_test_messages_y(self):
        message = dict(id='y', name='xxx_timestamp')
        message['text'] = '-i https://gals.kindgirls.com/d3/ariel_09328/m6/ariel_09328_8.jpg'
        message['timestamp'] = datetime.now().timestamp() - 28 * 24 * 60 * 60
        MESSAGES.append(message.copy())

    def add_test_messages_p(self):
        message = dict(id='p', name='xxx')
        message['text'] = '-t xxx задонатил и не сказал ничего.'
        MESSAGES.append(message.copy())
