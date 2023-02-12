from typing import Any
import asyncio

import websockets

from chat import Base
from common import MESSAGES, STATS
from config import CONFIG
from json_ import INSTANCEK as json

json.types_load = {'offset': int}


class Server(Base):
    names: list[str] = CONFIG['base'].getlist('names')
    tts_api_key: str = CONFIG['base'].get('tts_api_key')

    async def main(self) -> None:
        try:
            await self.on_start()
            async with websockets.serve(self.messages, '0.0.0.0', 55555):
                await asyncio.Future()
        except asyncio.CancelledError:
            await self.on_close()
            raise

    async def messages(self, websocket: Any) -> None:
        try:
            async for message in websocket:
                data = json.loads(message)
                offset = data.get('offset', 0)
                total = len(MESSAGES)
                if offset > total:
                    offset = 0
                await websocket.send(json.dumps({
                    'messages': MESSAGES.data[offset:],
                    'names': self.names,
                    'stats': STATS,
                    'total': total,
                    'tts_api_key': self.tts_api_key,
                }))
        except websockets.exceptions.ConnectionClosedError as e:
            await self.print_exception(e)
