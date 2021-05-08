import asyncio

from common import print_error


class Base():
    async def on_close(self) -> None:
        await self.print_error('{} остановлен.')

    async def on_start(self) -> None:
        await self.print_error('{} запущен.')

    async def print_error(self, pattern: str) -> None:
        await print_error(pattern.format(type(self).__name__))


class Chat(Base):
    def __init__(self, channel: str) -> None:
        self.channel = channel

    async def on_close(self) -> None:
        await super().on_close()
        await asyncio.sleep(5)

    async def print_error(self, pattern: str) -> None:
        await print_error(pattern.format(f'{type(self).__name__} (@{self.channel})'))
