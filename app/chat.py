import asyncio

from common import print_error


class Base():

    async def main(self):
        raise NotImplementedError

    async def print_error(self, pattern):
        await print_error(pattern.format(type(self).__name__))

    async def on_close(self):
        await self.print_error('{} остановлен.')

    async def on_start(self):
        await self.print_error('{} запущен.')


class Chat(Base):

    def __init__(self, channel):
        self.channel = channel

    async def main(self, session):
        raise NotImplementedError

    async def print_error(self, pattern):
        await print_error(pattern.format(f'{type(self).__name__} (@{self.channel})'))

    async def on_close(self):
        await super().on_close()
        await asyncio.sleep(5)
