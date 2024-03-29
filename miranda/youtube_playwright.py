import asyncio

from playwright.async_api import async_playwright, Locator

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

    async def main(self) -> None:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            page = await browser.new_page()
            await page.goto(f'https://www.youtube.com/live_chat?is_popout=1&v={self.channel}')
            await self.on_start()
            try:
                items = page.locator('#items.style-scope.yt-live-chat-item-list-renderer')
                while True:
                    for v in await items.locator('yt-live-chat-text-message-renderer').all():
                        await self.add_message(v)
                    await items.evaluate('(items) => items.innerHTML = ""')
                    await asyncio.sleep(TIMEOUT_5S)
            except asyncio.CancelledError:
                await browser.close()
                await self.on_close()
                raise
