import json
import html

import aiohttp

from chat import Chat
from common import MESSAGES
from config import CONFIG


class GoodGame(Chat):
    text = CONFIG['base'].getlist('text')

    async def main(self, session):
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

    async def on_open(self, w):
        data = {
            'type': 'join',
            'data': {
                'channel_id': self.channel,
                'hidden': False,
            },
        }
        await w.send_str(json.dumps(data))

    async def on_message(self, data):
        data = json.loads(data)
        if data['type'] == 'message':
            await self.add_message(data['data'])
        elif data['type'] == 'payment':
            await self.add_payment(data['data'])
        elif data['type'] == 'premium':
            await self.add_premium(data['data'])

    async def add_premium(self, data):
        text = CONFIG['goodgame']['text'].format(data['userName'])
        MESSAGES.append(dict(id='e', text=text))

    async def add_message(self, data):
        message = dict(id='g', name=data['user_name'],
                       text=html.unescape(data['text']),
                       premiums=data['premiums'])
        MESSAGES.append(message)

    async def add_payment(self, data):
        if data['message']:
            text = self.text[0].format(data['userName'], data['message'])
        else:
            text = self.text[1].format(data['userName'])
        MESSAGES.append(dict(id='p', text=text))
