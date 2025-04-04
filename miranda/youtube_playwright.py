import asyncio

from playwright.async_api import Locator, BrowserContext

from .chat import Chat
from .common import make_request, MESSAGES, STATS

TIMEOUT_10S: float = 10.0
TIMEOUT_5S: int = 5
TIMEOUT_15M: int = 15 * 60


class YouTube(Chat):
    async def add_message(self, message: Locator) -> None:
        try:
            for v in await message.locator('#message > img').all():
                attr = await v.get_attribute('src')
                if attr:
                    assert attr.startswith('https://fonts.gstatic.com/')
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


class YouTubeStats(Chat):
    """Статистика лайков и просмотров из RSS."""
    url: str = 'https://www.youtube.com/feeds/videos.xml?channel_id={}'

    async def add_stats(self, data: str) -> None:
        is_finded = False
        stats: list[str] = ['0', '0']
        for v in data.split('\n', 50):
            if f'<yt:videoId>{self.id}</yt:videoId>' in v:
                is_finded = True
            if is_finded and '<media:starRating count' in v:
                stats[1] = v.split('"')[1]
            if is_finded and '<media:statistics views' in v:
                stats[0] = v.split('"')[1]
                STATS['y'] = ', '.join(stats)
                break

    async def load(self) -> None:
        data = await make_request(self.url, timeout=TIMEOUT_10S, is_json=False)
        if data:
            await self.add_stats(data)

    async def main(self, id: str) -> None:
        try:
            await self.on_start()
            self.id = id
            self.url = self.url.format(self.channel)
            while True:
                await self.load()
                await asyncio.sleep(TIMEOUT_15M)
        except asyncio.CancelledError:
            await self.on_close()
            raise
