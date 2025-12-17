from datetime import datetime
from typing import Any
import asyncio
import importlib

from .chat import Base
from .common import MESSAGES, get_config_file, T, MessageABC, MessageMiranda
from .config import CONFIG, load
from .goodgame import Message as MG
from .twitch import Message as MT, Twitch
from .vkplay import Message as MV
from .youtube import Message as MY

TASKS: T = []
TG: asyncio.TaskGroup | None = None

config_mtime: float = get_config_file('config.ini').stat().st_mtime


async def start() -> None:
    if TASKS:
        return None
    if not TG:
        raise
    c = Commands()
    TASKS.append(TG.create_task(c.main()))
    TASKS.append(TG.create_task(c.reload_config()))


def shutdown() -> None:
    for task in TASKS:
        task.cancel()
    TASKS.clear()


class KillError(Exception):
    pass


class RestartError(Exception):
    pass


class Commands(Base):
    friendly: list[str]
    offset: int = 0
    root: list[str]
    start_timestamp: float = datetime.now().timestamp()

    def __init__(self) -> None:
        self.friendly = CONFIG['base'].getlist('friendly')
        self.root = CONFIG['base'].getlist('root')

    async def main(self) -> None:
        try:
            await self.on_start()
            commands = {}
            for k in CONFIG['commands']:
                commands[k] = CONFIG['commands'].getlist(k)
            while True:
                for message in MESSAGES[self.offset:]:
                    self.offset += 1
                    if type(message) is MessageMiranda:
                        continue
                    # Обработка имён.
                    is_root = self.is_root(message)
                    is_friendly = self.is_friendly(message)
                    # Параметры команды.
                    # p = ['имя метода', 'владелец', 'время с подписки']
                    for k, p in commands.items():
                        if message.text.startswith(k):
                            break
                    else:
                        continue
                    # Может ли пользователь использовать команду.
                    if is_root or \
                       (p[1] == 'follows' and is_friendly) or \
                       p[1] == '*' or \
                       (p[1] == 'follows' and self.is_timestamp(message, p)):
                        getattr(self, p[0])(
                            message=message,
                            command_text=message.text[len(k):].strip(),
                        )
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    async def reload_config(self) -> None:
        global config_mtime
        while True:
            await asyncio.sleep(5)
            mtime = get_config_file('config.ini').stat().st_mtime
            if mtime > config_mtime:
                config_mtime = mtime
                load()
                self.clean_messages()
                self.print_error('обновился config.ini.')
                raise RestartError

    def add_image(self, message: MessageABC, command_text: str) -> None:
        if command_text:
            k = '{image}'
            message.images[k] = command_text
            message.text = message.text.replace(command_text, k)

    def add_secret(self, **kwargs: Any) -> None:
        text = 'xxx'
        MESSAGES.append(MessageMiranda(text=text))

    def add_test_messages(self, **kwargs: Any) -> None:
        self.add_test_messages_t()
        self.add_test_messages_g()
        self.add_test_messages_s()
        self.add_test_messages_y()
        self.add_test_messages_d()

    def add_test_messages_g(self) -> None:
        name = 'chaos-soft'

        text = '-t от friendly'
        MESSAGES.append(MG(text=text, name=name))

        text = '-i https://gals.kindgirls.com/d11/ariel_09328/ariel_09328_9.jpg'
        MESSAGES.append(MG(text=text, name=name))

        text = ':peka: :gta: :bearbush:'
        MESSAGES.append(MG(text=text, name=name))

    def add_test_messages_d(self) -> None:
        text = 'xxx задонатил и не сказал ничего.'
        MESSAGES.append(MessageMiranda(text=text, is_donate=True))

    def add_test_messages_s(self) -> None:
        name = 'xxx'

        text = '-t от xxx'
        MESSAGES.append(MV(text=text, name=name))

        text = '-i https://gals.kindgirls.com/d11/ariel_09328/ariel_09328_10.jpg'
        MESSAGES.append(MV(text=text, name=name))

        text = '@chaos обращение'
        MESSAGES.append(MV(text=text, name=name))

    def add_test_messages_t(self) -> None:
        color = '#ff69b4'
        name = 'chaos_soft'
        t = Twitch('sle')

        text = '-t от root'
        MESSAGES.append(MT(text=text, name=name, color=color))

        text = '-i https://gals.kindgirls.com/d11/ariel_09328/ariel_09328_4.jpg'
        MESSAGES.append(MT(text=text, name=name, color=color))

        d = {
            'emotes': '555555562:3-4/555555589:6-7/555555584:12-13,15-16,18-19,25-26,28-29,31-32',
            'text': '<] >( ;) #/ <3 <3 <3 xxx <3 <3 <3',
        }
        t.parse_emotes(d)
        MESSAGES.append(MT(name=name, color=color, **d))

        d = {
            'emotes': '425618:0-2/245:4-18/81249:20-31',
            'text': 'LUL ResidentSleeper SeriousSloth',
        }
        t.parse_emotes(d)
        MESSAGES.append(MT(name=name, color=color, **d))

    def add_test_messages_y(self) -> None:
        name = 'xxx_timestamp'
        text = '-и https://gals.kindgirls.com/d11/ariel_09328/ariel_09328_10.jpg'
        timestamp = datetime.now().timestamp() - 28 * 24 * 60 * 60
        MESSAGES.append(MY(text=text, name=name, timestamp=timestamp))

    def add_tts(self, message: MessageABC, command_text: str) -> None:
        if command_text:
            text = command_text[:300]
            MESSAGES.append(MessageMiranda(text=text, is_tts=True))

    def clean_chat(self, **kwargs: Any) -> None:
        text = 'clean_chat'
        MESSAGES.append(MessageMiranda(text=text, is_js=True))

    def clean_messages(self, **kwargs: Any) -> None:
        MESSAGES[:] = []
        self.offset = 0
        self.clean_chat()

    def is_friendly(self, message: MessageABC) -> bool:
        name = message.name.lower()
        if name in self.friendly:
            message.name += ' [f]'
            return True
        else:
            return False

    def is_root(self, message: MessageABC) -> bool:
        name = message.name.lower()
        name_root = '{}:{}'.format(name, message.id)
        if name_root in self.root:
            message.name += ' [r]'
            return True
        else:
            return False

    def is_timestamp(self, message: MessageABC, params: list[str]) -> bool:
        is_timestamp = False
        try:
            timestamp = message.get('timestamp', self.start_timestamp)
            # Проверка времени с подписки.
            if self.start_timestamp - timestamp >= int(params[2]):
                is_timestamp = True
        except IndexError:
            is_timestamp = True
        return is_timestamp

    def kill(self, **kwargs: Any) -> None:
        raise KillError

    def print_to_console(self, message: MessageABC, command_text: str) -> None:
        if command_text:
            print(command_text)

    def shutdown(self, message: MessageABC, command_text: str) -> None:
        module_name = command_text
        if module_name not in CONFIG or not TG:
            return None
        module = importlib.import_module(f'miranda.{module_name}')
        module.shutdown()

    def start(self, message: MessageABC, command_text: str) -> None:
        module_name = command_text
        if module_name not in CONFIG or not TG:
            return None
        module = importlib.import_module(f'miranda.{module_name}')
        TG.create_task(module.start())
