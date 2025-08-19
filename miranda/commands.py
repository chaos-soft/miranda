from datetime import datetime
import asyncio

from . import vkplay_playwright
from . import youtube_playwright
from .chat import Base
from .common import D, EXCLUDE_IDS, MESSAGES
from .config import CONFIG

EXCLUDE_IDS.extend(['js', 'tts'])
INCLUDE_IDS: list[str] = ['p', 'e']


class CommandsError(Exception):
    pass


class Commands(Base):
    friendly: list[str] = CONFIG['base'].getlist('friendly')
    offset: int = 0
    root: list[str] = CONFIG['base'].getlist('root')
    start_timestamp: float = datetime.now().timestamp()

    async def add_image(self, message: D, command_text: str) -> None:
        if command_text:
            if 'replacements' not in message:
                message['replacements'] = []
            message['replacements'].append(command_text)

    async def add_role(self, message: D) -> None:
        name = message['name'].lower()
        if name in self.root:
            message['is_root'] = True
            message['name'] += ' [r]'
        elif name in self.friendly:
            message['is_friendly'] = True
            message['name'] += ' [f]'

    async def add_secret(self, **kwargs: D) -> None:
        MESSAGES.append(dict(id='m', text='xxx'))

    async def add_test_messages(self, **kwargs: D) -> None:
        await self.add_test_messages_t()
        await self.add_test_messages_g()
        await self.add_test_messages_s()
        await self.add_test_messages_y()
        await self.add_test_messages_p()

    async def add_test_messages_g(self) -> None:
        message = dict(id='g', name='chaos-soft', text='+t от friendly')
        MESSAGES.append(message.copy())
        message['text'] = '-i https://gals.kindgirls.com/d9/ariel_09328/ariel_09328_2.jpg'
        MESSAGES.append(message.copy())
        message['text'] = ':peka: :gta: :bearbush:'
        MESSAGES.append(message.copy())

    async def add_test_messages_p(self) -> None:
        message = dict(id='p', name='xxx')
        message['text'] = '+t xxx задонатил и не сказал ничего.'
        MESSAGES.append(message.copy())

    async def add_test_messages_s(self) -> None:
        message = dict(id='s', name='xxx', text='+t от xxx')
        MESSAGES.append(message.copy())
        message['text'] = '-i https://gals.kindgirls.com/d9/ariel_09328/ariel_09328_8.jpg'
        MESSAGES.append(message.copy())
        message['text'] = '@chaos обращение'
        MESSAGES.append(message.copy())

    async def add_test_messages_t(self) -> None:
        from . import twitch
        t = twitch.Twitch('sle')
        m = dict(id='t', name='chaos_soft', color='#ff69b4', text='+t от root')
        MESSAGES.append(m.copy())
        m['text'] = '-i https://gals.kindgirls.com/d9/ariel_25530/ariel_25530_2.jpg'
        MESSAGES.append(m.copy())
        m['text'] = '<] >( ;) #/ <3 <3 <3 xxx <3 <3 <3'
        m['emotes'] = '555555562:3-4/555555589:6-7/555555584:12-13,15-16,18-19,25-26,28-29,31-32'
        await t.parse_emotes(m)
        MESSAGES.append(m.copy())
        m['text'] = 'LUL ResidentSleeper SeriousSloth'
        m['emotes'] = '425618:0-2/245:4-18/81249:20-31'
        await t.parse_emotes(m)
        MESSAGES.append(m.copy())

    async def add_test_messages_y(self) -> None:
        message: D = dict(id='y', name='xxx_timestamp')
        message['text'] = '-и https://gals.kindgirls.com/d9/ariel_09328/ariel_09328_8.jpg'
        message['timestamp'] = datetime.now().timestamp() - 28 * 24 * 60 * 60
        MESSAGES.append(message.copy())

    async def add_tts(self, message: D, command_text: str) -> None:
        if command_text:
            MESSAGES.append(dict(id='tts', text=command_text[:300]))

    async def clean_chat(self, **kwargs: D) -> None:
        MESSAGES.append(dict(id='js', text='clean_chat'))

    async def clean_messages(self, **kwargs: D) -> None:
        MESSAGES[:] = []
        self.offset = 0
        await self.clean_chat()

    async def is_timestamp(self, message: D, params: list[str]) -> bool:
        is_timestamp = False
        try:
            timestamp = message.get('timestamp', self.start_timestamp)
            # Проверка времени с подписки.
            if self.start_timestamp - timestamp >= int(params[2]):
                is_timestamp = True
        except IndexError:
            is_timestamp = True
        return is_timestamp

    async def kill(self, **kwargs: D) -> None:
        await self.on_close()
        raise CommandsError

    async def main(self) -> None:
        try:
            await self.on_start()
            commands = {}
            for k in CONFIG['commands']:
                commands[k] = CONFIG['commands'].getlist(k)
            while True:
                for message in MESSAGES[self.offset:]:
                    self.offset += 1
                    if message['id'] in EXCLUDE_IDS:
                        continue
                    # В этих типах сообщений нет имен.
                    if message['id'] not in INCLUDE_IDS:
                        await self.add_role(message)
                    # Параметры команды.
                    # p = ['имя метода', 'владелец', 'время с подписки']
                    for k, p in commands.items():
                        if message['text'].startswith(k):
                            break
                    else:
                        continue
                    # Может ли пользователь использовать команду.
                    if message.get('is_root') or \
                       message['id'] in INCLUDE_IDS or \
                       (p[1] == 'follows' and message.get('is_friendly')) or \
                       p[1] == '*' or \
                       (p[1] == 'follows' and await self.is_timestamp(message, p)):
                        await getattr(self, p[0])(
                            message=message,
                            command_text=message['text'][len(k):].strip(),
                        )
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    async def print_to_console(self, message: D, command_text: str) -> None:
        if command_text:
            print(command_text)

    async def shutdown_vkplay_playwright(self, **kwargs: D) -> None:
        vkplay_playwright.shutdown()

    async def shutdown_youtube_playwright(self, **kwargs: D) -> None:
        youtube_playwright.shutdown()

    async def start_vkplay_playwright(self, **kwargs: D) -> None:
        await vkplay_playwright.start()

    async def start_youtube_playwright(self, **kwargs: D) -> None:
        await youtube_playwright.start()
