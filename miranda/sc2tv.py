import json

from .chat import WebSocket
from .common import D, MESSAGES


class Sc2tv(WebSocket):
    # Ping - 30 секунд, timeout - 60.
    heartbeat: int = 25
    heartbeat_data: str = '2'
    url: str = 'wss://chat.sc2tv.ru'

    async def add_message(self, data: D) -> None:
        if data['to']:
            text = f'{data["to"]["name"]}, {data["text"]}'
        else:
            text = data['text']
        message = dict(id='s', name=data['from']['name'], text=text)
        MESSAGES.append(message)

    async def join_chat(self) -> None:
        data = ['/chat/join', {'channel': f'stream/{self.channel}'}]
        await self.w.send(f'421{json.dumps(data)}')

    async def on_message(self, data_str: str) -> None:
        code = self.re_code.search(data_str).group(0)
        if code == '40':
            await self.join_chat()
        elif code == '42':
            data = json.loads(data_str.replace(code, '', 1))
            if data[1]['type'] == 'message':
                await self.add_message(data[1])
