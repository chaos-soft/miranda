from datetime import datetime
import asyncio

from .chat import Base
from .common import D, EXCLUDE_IDS, MESSAGES
from .config import CONFIG, load

EXCLUDE_IDS.extend(['js', 'tts'])
INCLUDE_IDS: list[str] = ['p', 'e']
TG: asyncio.TaskGroup | None = None


class CommandsError(Exception):
    pass


class Commands(Base):
    friendly: list[str] = CONFIG['base'].getlist('friendly')
    offset: int = 0
    root: list[str] = CONFIG['base'].getlist('root')
    start_timestamp: float = datetime.now().timestamp()

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
                        self.add_role(message)
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
                       (p[1] == 'follows' and self.is_timestamp(message, p)):
                        getattr(self, p[0])(
                            message=message,
                            command_text=message['text'][len(k):].strip(),
                        )
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    def add_image(self, message: D, command_text: str) -> None:
        if command_text:
            if 'replacements' not in message:
                message['replacements'] = []
            message['replacements'].append(command_text)

    def add_role(self, message: D) -> None:
        name = message['name'].lower()
        if name in self.root:
            message['is_root'] = True
            message['name'] += ' [r]'
        elif name in self.friendly:
            message['is_friendly'] = True
            message['name'] += ' [f]'

    def add_secret(self, **kwargs: D) -> None:
        MESSAGES.append(dict(id='m', text='xxx'))

    def add_test_messages(self, **kwargs: D) -> None:
        self.add_test_messages_t()
        self.add_test_messages_g()
        self.add_test_messages_s()
        self.add_test_messages_y()
        self.add_test_messages_p()

    def add_test_messages_g(self) -> None:
        message = dict(id='g', name='chaos-soft', text='+t от friendly')
        MESSAGES.append(message.copy())
        message['text'] = '-i https://gals.kindgirls.com/d11/ariel_09328/ariel_09328_9.jpg'
        MESSAGES.append(message.copy())
        message['text'] = ':peka: :gta: :bearbush:'
        MESSAGES.append(message.copy())

    def add_test_messages_p(self) -> None:
        message = dict(id='p', name='xxx')
        message['text'] = '+t xxx задонатил и не сказал ничего.'
        MESSAGES.append(message.copy())

    def add_test_messages_s(self) -> None:
        message = dict(id='s', name='xxx', text='+t от xxx')
        MESSAGES.append(message.copy())
        message['text'] = '-i https://gals.kindgirls.com/d11/ariel_09328/ariel_09328_10.jpg'
        MESSAGES.append(message.copy())
        message['text'] = '@chaos обращение'
        MESSAGES.append(message.copy())

    def add_test_messages_t(self) -> None:
        from . import twitch
        t = twitch.Twitch('sle')
        m = dict(id='t', name='chaos_soft', color='#ff69b4', text='+t от root')
        MESSAGES.append(m.copy())
        m['text'] = '-i https://gals.kindgirls.com/d11/ariel_09328/ariel_09328_4.jpg'
        MESSAGES.append(m.copy())
        m['text'] = '<] >( ;) #/ <3 <3 <3 xxx <3 <3 <3'
        m['emotes'] = '555555562:3-4/555555589:6-7/555555584:12-13,15-16,18-19,25-26,28-29,31-32'
        t.parse_emotes(m)
        MESSAGES.append(m.copy())
        m['text'] = 'LUL ResidentSleeper SeriousSloth'
        m['emotes'] = '425618:0-2/245:4-18/81249:20-31'
        t.parse_emotes(m)
        MESSAGES.append(m.copy())

    def add_test_messages_y(self) -> None:
        message: D = dict(id='y', name='xxx_timestamp')
        message['text'] = '-и https://gals.kindgirls.com/d11/ariel_09328/ariel_09328_10.jpg'
        message['timestamp'] = datetime.now().timestamp() - 28 * 24 * 60 * 60
        MESSAGES.append(message.copy())

    def add_tts(self, message: D, command_text: str) -> None:
        if command_text:
            MESSAGES.append(dict(id='tts', text=command_text[:300]))

    def clean_chat(self, **kwargs: D) -> None:
        MESSAGES.append(dict(id='js', text='clean_chat'))

    def clean_messages(self, **kwargs: D) -> None:
        MESSAGES[:] = []
        self.offset = 0
        self.clean_chat()

    def is_timestamp(self, message: D, params: list[str]) -> bool:
        is_timestamp = False
        try:
            timestamp = message.get('timestamp', self.start_timestamp)
            # Проверка времени с подписки.
            if self.start_timestamp - timestamp >= int(params[2]):
                is_timestamp = True
        except IndexError:
            is_timestamp = True
        return is_timestamp

    def kill(self, **kwargs: D) -> None:
        raise CommandsError

    def print_to_console(self, message: D, command_text: str) -> None:
        if command_text:
            print(command_text)

    def reload_config(self, **kwargs: D) -> None:
        load()

    def shutdown_youtube(self, **kwargs: D) -> None:
        from . import youtube
        youtube.shutdown()

    def shutdown_youtube_playwright(self, **kwargs: D) -> None:
        from . import youtube_playwright
        youtube_playwright.shutdown()

    def start_youtube(self, **kwargs: D) -> None:
        if not TG:
            raise
        from . import youtube
        TG.create_task(youtube.start())

    def start_youtube_playwright(self, **kwargs: D) -> None:
        if not TG:
            raise
        from . import youtube_playwright
        TG.create_task(youtube_playwright.start())
