from typing import Any, Union
import asyncio
import re

import aiohttp

from common import print_error


class Base():
    async def on_close(self) -> None:
        await self.print_error('остановлен')

    async def on_start(self) -> None:
        await self.print_error('запущен')

    async def print_error(self, str_: str) -> None:
        await print_error(f'{type(self).__name__} {str_}.')


class Chat(Base):
    def __init__(self, channel: Union[int, str]) -> None:
        self.channel = channel

    async def on_close(self) -> None:
        await super().on_close()
        await asyncio.sleep(5)

    async def print_error(self, str_: str) -> None:
        await print_error(f'{type(self).__name__} ({self.channel}) {str_}.')


class WebSocket(Chat):
    heartbeat: int = 0
    re_code: Any = re.compile(r'^\d+')
    url: str = ''
    w: Any = None

    async def main(self, session: Any) -> None:
        while True:
            await self.on_start()
            try:
                async with session.ws_connect(self.url) as self.w:
                    await self.on_open()
                    async for message in self.w:
                        if message.type == aiohttp.WSMsgType.TEXT:
                            await self.on_message(message.data.strip())
                        else:
                            if message.type == aiohttp.WSMsgType.CLOSE:
                                await self.w.close()
                            elif message.type == aiohttp.WSMsgType.ERROR:
                                await self.print_error(self.w.exception())
                            elif message.type == aiohttp.WSMsgType.CLOSED:
                                pass
                            break
            except aiohttp.client_exceptions.ClientError as e:
                await self.print_error(f'{type(e).__name__}: {e}')
            self.w = None
            await self.on_close()

    async def on_message(self, data_str: str) -> None:
        raise NotImplementedError

    async def on_open(self) -> None:
        pass

    async def send_heartbeat(self) -> None:
        while True:
            await asyncio.sleep(self.heartbeat)
            if self.w:
                await self.w.send_str('2')
