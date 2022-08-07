from datetime import datetime
import asyncio

from chat import Base
from common import D, EXCLUDE_IDS, MESSAGES
from config import CONFIG

EXCLUDE_IDS.extend(['js', 'tts'])
INCLUDE_IDS = ['p', 'e']


class Commands(Base):
    friendly = CONFIG['base'].getlist('friendly')
    offset = 0
    root = CONFIG['base'].getlist('root')
    start_timestamp = datetime.now().timestamp()

    async def main(self):
        await self.on_start()
        commands = {}
        for k in CONFIG['commands']:
            commands[k] = CONFIG['commands'].getlist(k)
        while True:
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
                # В этих типах сообщений нет имен.
                if message['id'] not in INCLUDE_IDS:
                    await self.add_role(message)
                # Может ли пользователь использовать команду.
                if message.get('is_root') or \
                   message['id'] in INCLUDE_IDS or \
                   (p[1] == 'follows' and message.get('is_friendly')) or \
                   p[1] == '*' or \
                   (p[1] == 'follows' and await self.is_timestamp(message, p)):
                    await getattr(self, p[0])(
                        message=message,
                        command_text=message['text'][len(k):].strip())
            await asyncio.sleep(0.5)

    async def is_timestamp(self, message, params):
        is_timestamp = False
        try:
            timestamp = message.get('timestamp', self.start_timestamp)
            # Проверка времени с подписки.
            if self.start_timestamp - timestamp >= int(params[2]):
                is_timestamp = True
        except IndexError:
            is_timestamp = True
        return is_timestamp

    async def add_role(self, message):
        name = message['name'].lower()
        if name in self.root:
            message['is_root'] = True
        elif name in self.friendly:
            message['is_friendly'] = True

    async def add_tts(self, message, command_text):
        if command_text:
            MESSAGES.append(dict(id='tts', text=command_text[:300]))

    async def add_image(self, message, command_text):
        if command_text:
            if 'replacements' not in message:
                message['replacements'] = []
            message['replacements'].append(command_text)

    async def clean_chat(self, **kwargs):
        MESSAGES.append(dict(id='js', text='clean_chat'))

    async def print_to_console(self, message, command_text):
        if command_text:
            print(command_text)

    async def clean_messages(self, **kwargs):
        MESSAGES[:] = []
        self.offset = 0
        await self.clean_chat()

    async def add_test_messages(self, **kwargs):
        await self.add_test_messages_t()
        await self.add_test_messages_g()
        await self.add_test_messages_s()
        await self.add_test_messages_p()

    async def add_test_messages_t(self):
        import twitch
        t = twitch.Twitch('sle')
        m = dict(id='t', name='chaos_soft', color='#ff69b4', text='-t от root')
        MESSAGES.append(m.copy())
        m['text'] = '-i https://gals.kindgirls.com/d009/ariel_25530/ariel_25530_2.jpg'
        MESSAGES.append(m.copy())
        m['text'] = '<] >( ;) #/ <3 <3 <3 xxx <3 <3 <3'
        m['emotes'] = '555555562:3-4/555555589:6-7/555555584:12-13,15-16,18-19,25-26,28-29,31-32'
        await t.parse_emotes(m)
        MESSAGES.append(m.copy())
        m['text'] = 'LUL ResidentSleeper SeriousSloth'
        m['emotes'] = '425618:0-2/245:4-18/81249:20-31'
        await t.parse_emotes(m)
        MESSAGES.append(m.copy())

    async def add_test_messages_g(self):
        message = dict(id='g', name='chaos-soft', text='-t от friendly')
        MESSAGES.append(message.copy())
        message['text'] = '-i https://gals.kindgirls.com/d009/ariel_09328/ariel_09328_2.jpg'
        MESSAGES.append(message.copy())
        message['text'] = ':peka: :gta: :bearbush:'
        MESSAGES.append(message.copy())

    async def add_test_messages_s(self):
        message = dict(id='g', name='xxx', text='-t от xxx')
        MESSAGES.append(message.copy())
        message['text'] = '-i https://gals.kindgirls.com/d009/ariel_09328/ariel_09328_8.jpg'
        MESSAGES.append(message.copy())
        message['name'] = 'xxx_timestamp'
        message['timestamp'] = datetime.now().timestamp() - 28 * 24 * 60 * 60
        MESSAGES.append(message.copy())
        message['text'] = '@chaos обращение'
        MESSAGES.append(message.copy())

    async def add_test_messages_p(self):
        message = dict(id='p', name='xxx')
        message['text'] = '-t xxx задонатил и не сказал ничего.'
        MESSAGES.append(message.copy())

    async def add_secret(self, **kwargs):
        MESSAGES.append(dict(id='m', text='xxx'))

    async def add_wasd(self, message: D, command_text: str) -> None:
        CONFIG['wasd']['stream'], CONFIG['wasd']['channel'], CONFIG['wasd']['jwt'] = \
            command_text.split('@')
