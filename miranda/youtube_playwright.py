import asyncio

from playwright.async_api import Locator, BrowserContext

from .chat import Chat
from .common import MESSAGES

TIMEOUT_5S: int = 5


class YouTube(Chat):
    async def add_message(self, message: Locator) -> None:
        try:
            for v in await message.locator('#message > img').all():
                assert (await v.get_attribute('src')).startswith('https://www.youtube.com/s/gaming/emoji/')
            MESSAGES.extend([dict(
                id='y',
                name=await message.locator('#author-name').inner_text(),
                text=await message.locator('#message').inner_html(),
            )])
        except AssertionError:
            MESSAGES.append(dict(
                id='y',
                name=await message.locator('#author-name').inner_text(),
                text=await message.locator('#message').inner_text(),
            ))

    async def main(self, context: BrowserContext) -> None:
        page = await context.new_page()
        await page.goto(f'https://www.youtube.com/live_chat?is_popout=1&v={self.channel}')
        await self.on_start()
        # Все сообщения.
        await page.locator('#trigger.style-scope.tp-yt-paper-menu-button').click()
        await page.locator('a.yt-simple-endpoint.style-scope.yt-dropdown-menu').nth(1).click()
        items = page.locator('#items.style-scope.yt-live-chat-item-list-renderer')
        try:
            while True:
                for v in await items.locator('yt-live-chat-text-message-renderer').all():
                    await self.add_message(v)
                await items.evaluate('(items) => items.innerHTML = ""')
                await asyncio.sleep(TIMEOUT_5S)
        except asyncio.CancelledError:
            await self.on_close()
            raise
