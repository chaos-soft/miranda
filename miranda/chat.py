from abc import ABCMeta, abstractmethod
import asyncio

import websockets

from .common import print_error


class Base(metaclass=ABCMeta):
    async def on_close(self) -> None:
        self.print_error('остановлен.')

    async def on_start(self, str_: str = '') -> None:
        if str_:
            self.print_error(f'{str_} запущен.')
        else:
            self.print_error('запущен.')

    def print_error(self, str_: str) -> None:
        print_error(f'{type(self).__name__} {str_}')

    def print_exception(self, e: Exception) -> None:
        self.print_error(f'{type(e).__name__}: {e}')


class Chat(Base):
    channel: str

    def __init__(self, channel: str) -> None:
        self.channel = channel

    def print_error(self, str_: str) -> None:
        print_error(f'{type(self).__name__} ({self.channel}) {str_}')


class WebSocket(Chat):
    heartbeat_data: str
    url: str
    w: websockets.ClientConnection | None = None

    async def main(self) -> None:
        try:
            async for self.w in websockets.connect(self.url):
                try:
                    await self.on_start()
                    await self.on_open()
                    async for message in self.w:
                        await self.on_message(str(message).strip())
                except websockets.ConnectionClosed as e:
                    self.print_exception(e)
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

    @abstractmethod
    async def on_message(self, data_str: str) -> None:
        pass

    async def on_open(self) -> None:
        pass

    async def send_heartbeat(self) -> None:
        if self.w:
            try:
                await self.w.send(self.heartbeat_data)
            except websockets.ConnectionClosed:
                pass
