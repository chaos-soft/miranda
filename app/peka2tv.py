import json
import re
import types
from datetime import datetime, timedelta

import aiohttp

from chat import Chat
from common import MESSAGES

# Ping - 30 секунд, timeout - 60.
PING_TIMEOUT = 25


def _send_heartbeat(self):
    self.ping_time = datetime.now() + timedelta(seconds=PING_TIMEOUT)
    self._loop.create_task(self._writer.send('2', binary=False, compress=None))


class Peka2tv(Chat):
    re_code = re.compile(r'^\d+')

    async def main(self, session):
        while True:
            await self.on_start()
            async with session.ws_connect('wss://chat.sc2tv.ru', heartbeat=PING_TIMEOUT) as w:
                # Ориентировочное время отсылки PING.
                w.ping_time = datetime.now() + timedelta(seconds=PING_TIMEOUT)
                w._send_heartbeat = types.MethodType(_send_heartbeat, w)
                async for message in w:
                    if message.type == aiohttp.WSMsgType.TEXT:
                        await self.on_message(message.data, w)
                    elif message.type == aiohttp.WSMsgType.ERROR:
                        break
                    if w.ping_time <= datetime.now():
                        w._send_heartbeat()
                await w.close()
            await self.on_close()

    async def on_message(self, data, w):
        code = self.re_code.search(data).group(0)
        if code == '40':
            await self.join_chat(w)
        elif code == '42':
            data = json.loads(data.replace(code, '', 1))
            if data[1]['type'] == 'message':
                await self.add_message(data[1])

    async def join_chat(self, w):
        data = ['/chat/join', {'channel': f'stream/{self.channel}'}]
        await w.send_str(f'421{json.dumps(data)}')

    async def add_message(self, data):
        if data['to']:
            text = f'{data["to"]["name"]}, {data["text"]}'
        else:
            text = data['text']
        message = dict(id='s', name=data['from']['name'], text=text)
        MESSAGES.append(message)
