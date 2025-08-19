from typing import Any
import asyncio

from playwright._impl._errors import TimeoutError
from playwright.async_api import Locator, Page, async_playwright

from .chat import Chat
from .common import make_request, MESSAGES, STATS
from .config import CONFIG

TASKS: list[asyncio.Task[None]] = []
TG: asyncio.TaskGroup | None = None
TIMEOUT_1S: int = 1
TIMEOUT_30SF: float = 30.0
TIMEOUT_5M: int = 5 * 60
TIMEOUT_5S: int = 5

video_id: str = ''


async def start() -> None:
    if 'youtube_playwright' not in CONFIG or TASKS:
        return None
    if not TG:
        raise
    channel = CONFIG['youtube_playwright'].get('channel')
    TASKS.append(TG.create_task(YouTube('xxx').main()))
    TASKS.append(TG.create_task(YouTubeStats(channel).main()))


def shutdown() -> None:
    for task in TASKS:
        task.cancel()
    STATS['y'] = ''


class YouTube(Chat):
    browser: Any
    page: Page
    playwright: Any
    url: str = 'youtube.com'

    async def add_message(self, message: Locator) -> None:
        MESSAGES.extend([dict(
            id='y',
            name=await message.locator('#author-name').inner_text(),
            text=await message.locator('#message').inner_html(),
        )])

    async def main(self) -> None:
        while True:
            if not video_id:
                await asyncio.sleep(TIMEOUT_5S)
            else:
                self.channel = video_id
                await self.start()
                break

        try:
            page = self.page
            await page.route('**/*', self.handle_route)
            await page.goto(f'https://www.youtube.com/live_chat?is_popout=1&v={video_id}')
            await self.on_start()
            # Все сообщения.
            await page.locator('#trigger.style-scope.tp-yt-paper-menu-button').click()
            await page.locator('a.yt-simple-endpoint.style-scope.yt-dropdown-menu').nth(1).click()
            await asyncio.sleep(TIMEOUT_1S)
            items = page.locator('#items.style-scope.yt-live-chat-item-list-renderer')
            while True:
                for v in await items.locator('yt-live-chat-text-message-renderer').all():
                    await self.add_message(v)
                await items.evaluate('(items) => items.innerHTML = ""')
                await asyncio.sleep(TIMEOUT_5S)
        except asyncio.CancelledError:
            await self.on_close()
            raise
        except TimeoutError as e:
            await self.print_exception(e)
            await self.on_close()
        finally:
            await self.browser.close()
            await self.playwright.stop()

    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.firefox.launch(headless=True)
        context = await self.browser.new_context()
        self.page = await context.new_page()


class YouTubeStats(Chat):
    """Статистика лайков и просмотров из RSS."""
    url: str = 'https://www.youtube.com/feeds/videos.xml?channel_id={}'

    async def add_stats(self, data: str) -> None:
        stats: list[str] = ['0', '0']
        for v in data.split('\n', 50):
            if '<yt:videoId>' in v:
                global video_id
                video_id = v.split('>')[1].split('<')[0]
            if '<media:starRating count' in v:
                stats[1] = v.split('"')[1]
            if '<media:statistics views' in v:
                stats[0] = v.split('"')[1]
                STATS['y'] = ', '.join(stats)
                break

    async def load(self) -> None:
        data = await make_request(self.url, timeout=TIMEOUT_30SF, is_json=False)
        if data:
            await self.add_stats(data)

    async def main(self) -> None:
        await self.on_start()
        self.url = self.url.format(self.channel)
        try:
            while True:
                await self.load()
                await asyncio.sleep(TIMEOUT_5M)
        except asyncio.CancelledError:
            await self.on_close()
            raise
