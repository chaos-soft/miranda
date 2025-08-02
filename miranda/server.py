from typing import Any
import asyncio

import websockets

from .chat import Base
from .common import MESSAGES, STATS
from .config import CONFIG
from .tipizator import Tipizator

tipizator = Tipizator(types_load={'offset': int, 'code': str})


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
                data = tipizator.loads(message)
                offset = data.get('offset', 0)
                total = len(MESSAGES)
                if offset > total:
                    offset = 0
                await websocket.send(tipizator.dumps({
                    'messages': MESSAGES.data[offset:],
                    'names': self.names,
                    'stats': STATS,
                    'total': total,
                    'tts_api_key': self.tts_api_key,
                }))
                for v in ['youtube', 'twitch']:
                    if v in CONFIG:
                        CONFIG[v]['code'] = data.get(v, '')
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
            await self.print_exception(e)
