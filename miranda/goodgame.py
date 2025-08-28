import asyncio
import json

from .chat import WebSocket
from .common import D, MESSAGES, STATS, T
from .config import CONFIG

TASKS: T = []
TG: asyncio.TaskGroup | None = None


async def start() -> None:
    if 'goodgame' not in CONFIG or TASKS:
        return None
    if not TG:
        raise
    for channel in CONFIG['goodgame'].getlist('channels'):
        g = GoodGame(channel)
        TASKS.append(TG.create_task(g.main()))
        TASKS.append(TG.create_task(g.send_heartbeat()))


def shutdown() -> None:
    for task in TASKS:
        task.cancel()
    TASKS.clear()


class GoodGame(WebSocket):
    heartbeat: int = 20
    heartbeat_data: str = json.dumps({'type': 'ping', 'data': {}})
    text_donate: str = CONFIG['base']['text_donate']
    text_donate_empty: str = CONFIG['base']['text_donate_empty']
    url: str = 'wss://chat-1.goodgame.ru/chat2/'

    async def on_message(self, data_str: str) -> None:
        data = json.loads(data_str)
        if data['type'] == 'channel_counters':
            self.add_stats(data['data'])
        elif data['type'] == 'message':
            self.add_message(data['data'])
        elif data['type'] == 'payment':
            self.add_payment(data['data'])
        elif data['type'] == 'premium':
            self.add_premium(data['data'])
        elif data['type'] == 'follower':
            self.add_follower(data['data'])
        elif data['type'] == 'teleport_aim':
            self.add_teleport(data['data'])

    async def on_open(self) -> None:
        data = {
            'data': {
                'channel_id': self.channel,
                'hidden': 0,
                'reload': False,
            },
            'type': 'join',
        }
        await self.w.send(json.dumps(data))
        self.add_info()

    def add_follower(self, data: D) -> None:
        text = CONFIG['goodgame']['text_follower'].format(data['userName'])
        MESSAGES.append(dict(id='e', text=text))

    def add_info(self) -> None:
        MESSAGES.append(dict(id='m', text='Статистика с GoodGame: онлайн, в чате.'))

    def add_message(self, data: D) -> None:
        MESSAGES.append(dict(id='g', name=data['user_name'], text=data['text'], premiums=data['premiums']))

    def add_payment(self, data: D) -> None:
        if data['message']:
            text = self.text_donate.format(data['userName'], data['message'])
        else:
            text = self.text_donate_empty.format(data['userName'])
        MESSAGES.append(dict(id='p', text=text))

    def add_premium(self, data: D) -> None:
        text = CONFIG['goodgame']['text_premium'].format(data['userName'])
        MESSAGES.append(dict(id='e', text=text))

    def add_stats(self, data: D) -> None:
        STATS['g'] = f"{data['clients_in_channel']} {data['users_in_channel']}"

    def add_teleport(self, data: D) -> None:
        text = CONFIG['goodgame']['text_teleport'].format(data['streamerUsernameSrc'], data['usersCnt'])
        MESSAGES.append(dict(id='e', text=text))
