from typing import Any
import asyncio

import websockets

from .chat import Base
from .common import MESSAGES, STATS
from .config import CONFIG
from .tipizator import Tipizator

tipizator = Tipizator(types_load={'offset': int})


class Server(Base):
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
                    'messages': MESSAGES[offset:],
                    'names': CONFIG['base'].getlist('names'),
                    'stats': STATS,
                    'total': total,
                    'tts_api_key': CONFIG['base'].get('tts_api_key'),
                }))
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
            self.print_exception(e)
