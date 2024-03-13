from typing import Any, Union
import asyncio
import re

import websockets

from .common import print_error


class Base():
    async def on_close(self) -> None:
        await self.print_error('остановлен')

    async def on_start(self) -> None:
        await self.print_error('запущен')

    async def print_error(self, str_: str) -> None:
        await print_error(f'{type(self).__name__} {str_}.')

    async def print_exception(self, e: Exception) -> None:
        await self.print_error(f'{type(e).__name__}: {e}')


class Chat(Base):
    def __init__(self, channel: Union[int, str]) -> None:
        self.channel = channel

    async def print_error(self, str_: str) -> None:
        await print_error(f'{type(self).__name__} ({self.channel}) {str_}.')


class WebSocket(Chat):
    heartbeat: int = 0
    heartbeat_data: str = ''
    re_code: Any = re.compile(r'^\d+')
    url: str = ''
    w: Any = None

    async def main(self) -> None:
        try:
            async for self.w in websockets.connect(self.url):
                try:
                    await self.on_start()
                    await self.on_open()
                    async for message in self.w:
                        await self.on_message(message.strip())
                except websockets.ConnectionClosed as e:
                    await self.print_exception(e)
                    await self.on_close()
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    async def on_close(self) -> None:
        if self.w:
            await self.w.close()
        self.w = None
        await super().on_close()

    async def on_message(self, data_str: str) -> None:
        raise NotImplementedError

    async def on_open(self) -> None:
        pass

    async def send_heartbeat(self) -> None:
        while True:
            await asyncio.sleep(self.heartbeat)
            if self.w:
                try:
                    await self.w.send(self.heartbeat_data)
                except websockets.ConnectionClosed:
                    pass
