import asyncio

from playwright.async_api import Locator, BrowserContext

from .chat import Chat
from .common import MESSAGES, STATS

TIMEOUT_5S: int = 5


class VKPlay(Chat):
    async def add_message(self, message: Locator) -> None:
        name = await message.locator('[data-role=messageAuthor]').inner_text()
        MESSAGES.extend([dict(
            id='v',
            name=name.rstrip(':'),
            text=await message.locator('[data-role=messageMainContent]').inner_html(),
        )])

    async def add_stats(self, stats: Locator) -> None:
        if await stats.count():
            STATS['v'] = await stats.inner_text()
        else:
            STATS['v'] = ''

    async def main(self, context: BrowserContext) -> None:
        page = await context.new_page()
        await page.goto(f'https://live.vkvideo.ru/{self.channel}/only-chat')
        await self.on_start()
        items = page.locator('data-test-id=ChatMessage:root')
        stats = page.locator('xpath=/html/body/div[1]/div/div/div/div/div[2]/div[1]/div[1]/div/div/span')
        try:
            while True:
                for v in await items.all():
                    await self.add_message(v)
                i = await items.count() - 1
                while i >= 0:
                    await items.nth(i).evaluate('(v) => v.parentElement.remove()')
                    i -= 1
                await self.add_stats(stats)
                await asyncio.sleep(TIMEOUT_5S)
        except asyncio.CancelledError:
            await self.on_close()
            raise
