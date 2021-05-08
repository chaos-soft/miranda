from datetime import datetime
from typing import Any, List
import json

import aiohttp

from chat import Chat
from common import D, MESSAGES, TIMEOUT_STATS
from config import CONFIG


class GoodGame(Chat):
    is_stats: bool = CONFIG['base'].getboolean('is_stats')
    last_ts: int = 0
    text: List[str] = CONFIG['base'].getlist('text')

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
        current_ts = int(datetime.now().timestamp())
        if current_ts - self.last_ts >= TIMEOUT_STATS:
            self.last_ts = current_ts
            message = dict(id='js', text='refresh_stats', sid='g',
                           stext=f'{data["users_in_channel"]}, {data["clients_in_channel"]}')
            MESSAGES.append(message)

    async def main(self, session: Any) -> None:
        while True:
            await self.on_start()
            async with session.ws_connect('wss://chat.goodgame.ru/chat/websocket') as w:
                await self.on_open(w)
                async for message in w:
                    if message.type == aiohttp.WSMsgType.TEXT:
                        await self.on_message(message.data)
                    elif message.type == aiohttp.WSMsgType.ERROR:
                        break
                await w.close()
            await self.on_close()

    async def on_message(self, data_str: str) -> None:
        data = json.loads(data_str)
        if data['type'] == 'channel_counters' and self.is_stats:
            await self.add_stats(data['data'])
        elif data['type'] == 'message':
            await self.add_message(data['data'])
        elif data['type'] == 'payment':
            await self.add_payment(data['data'])
        elif data['type'] == 'premium':
            await self.add_premium(data['data'])

    async def on_open(self, w: Any) -> None:
        data = {
            'type': 'join',
            'data': {
                'channel_id': self.channel,
                'hidden': False,
            },
        }
        await w.send_str(json.dumps(data))
