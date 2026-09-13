from typing import Any
import asyncio

from websockets.asyncio.server import serve  # type: ignore
import websockets  # type: ignore

from .chat import Base
from .common import MESSAGES, MESSAGES_EVENT, STATS, messages_to_dict
from .config import CONFIG
from .tipizator import Tipizator


class Server(Base):
    lock: asyncio.Lock
    tipizator: Tipizator = Tipizator(types_dump={"messages": messages_to_dict})

    def __init__(self) -> None:
        self.lock = asyncio.Lock()

    async def handler(self, websocket: Any) -> None:
        offset = await self.send_messages(websocket, offset=-10)
        try:
            while True:
                await MESSAGES_EVENT.wait()
                MESSAGES_EVENT.clear()
                offset = await self.send_messages(websocket, offset)
        except websockets.exceptions.ConnectionClosedError as e:
            self.print_exception(e)
        except websockets.exceptions.ConnectionClosedOK:
            pass
        except asyncio.CancelledError:
            await websocket.close()
            raise

    async def main(self) -> None:
        host = CONFIG["base"].get("host", "0.0.0.0")
        port = CONFIG["base"].getint("port", 55555)
        server = None
        try:
            await self.on_start()
            server = await serve(self.handler, host, port)
            await server.wait_closed()
        except asyncio.CancelledError:
            if server:
                server.close()
            await self.on_close()
            raise

    async def send_messages(self, websocket: Any, offset: int) -> int:
        async with self.lock:
            total = len(MESSAGES)
            if offset > total:
                offset = 0
            new_messages = MESSAGES[offset:]
            data = self.tipizator.dumps(
                {
                    "messages": new_messages,
                    "names": CONFIG["base"].getlist("names"),
                    "stats": STATS,
                    "total": total,
                    "tts_api_key": CONFIG["base"].get("tts_api_key"),
                }
            )

        await websocket.send(data)
        return total
