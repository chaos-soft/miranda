from typing import Any
import asyncio
import json

from chat import WebSocket
from common import D, MESSAGES, STATS
from config import CONFIG


class WASD(WebSocket):
    # Ping - 25 секунд, timeout - 5.
    heartbeat: int = 20
    jwt: str = CONFIG['wasd'].get('jwt')
    stream: int = CONFIG['wasd'].getint('stream')
    url: str = 'wss://chat.wasd.tv/socket.io/?EIO=3&transport=websocket'

    async def add_message(self, data: D) -> None:
        message = dict(id='w', name=data['user_login'], text=data['message'])
        MESSAGES.append(message)

    async def add_stats(self, data: D) -> None:
        STATS['w'] = data['total']

    async def add_sticker(self, data: D) -> None:
        message = dict(id='w', name=data['user_login'], text='image0')
        message['replacements'] = [[
            'image0',
            data['sticker']['sticker_image']['medium'],
        ]]
        MESSAGES.append(message)

    async def join_chat(self) -> None:
        data = ['join', {
            'channelId': self.channel,
            'jwt': self.jwt,
            'streamId': self.stream,
        }]
        await self.w.send_str(f'42{json.dumps(data)}')

    async def main(self, session: Any) -> None:
        while True:
            if not self.channel:
                await asyncio.sleep(5)
                self.channel = CONFIG['wasd'].getint('channel')
                self.jwt = CONFIG['wasd'].get('jwt')
                self.stream = CONFIG['wasd'].getint('stream')
                continue
            await super().main(session)

    async def on_message(self, data_str: str) -> None:
        code = self.re_code.search(data_str).group(0)
        if code == '40':
            await self.join_chat()
        elif code == '42':
            data = json.loads(data_str.replace(code, '', 1))
            if data[0] == 'message':
                await self.add_message(data[1])
            elif data[0] == 'sticker':
                await self.add_sticker(data[1])
            elif data[0] == 'viewers':
                await self.add_stats(data[1])
