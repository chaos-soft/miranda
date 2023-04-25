import json

from .chat import WebSocket
from .common import D, MESSAGES, STATS
from .config import CONFIG


class GoodGame(WebSocket):
    heartbeat: int = 20
    heartbeat_data: str = json.dumps({'type': 'ping', 'data': {}})
    text: list[str] = CONFIG['base'].getlist('text')
    url: str = 'wss://chat-1.goodgame.ru/chat2/'

    async def add_message(self, data: D) -> None:
        message = dict(id='g', name=data['user_name'], text=data['text'],
                       premiums=data['premiums'])
        MESSAGES.append(message)

    async def add_payment(self, data: D) -> None:
        if data['message']:
            text = self.text[0].format(data['userName'], data['message'])
        else:
            text = self.text[1].format(data['userName'])
        MESSAGES.append(dict(id='p', text=text))

    async def add_premium(self, data: D) -> None:
        text = CONFIG['goodgame']['text'].format(data['userName'])
        MESSAGES.append(dict(id='e', text=text))

    async def add_stats(self, data: D) -> None:
        STATS['g'] = f"{data['clients_in_channel']}, {data['users_in_channel']}"

    async def on_message(self, data_str: str) -> None:
        data = json.loads(data_str)
        if data['type'] == 'channel_counters':
            await self.add_stats(data['data'])
        elif data['type'] == 'message':
            await self.add_message(data['data'])
        elif data['type'] == 'payment':
            await self.add_payment(data['data'])
        elif data['type'] == 'premium':
            await self.add_premium(data['data'])

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
