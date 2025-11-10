from typing import Any
import asyncio

from playwright._impl._errors import TimeoutError
from playwright.async_api import Locator, Page, async_playwright, Route

from .chat import Chat
from .common import MESSAGES, T, start_after, STATS, MessageABC, MessageMiranda
from .config import CONFIG
from .youtube_rss import YouTubeStats, video_id

TASKS: T = []
TG: asyncio.TaskGroup | None = None
TIMEOUT_1S: int = 1
TIMEOUT_30S: int = 30
TIMEOUT_30SF: float = 30.0
TIMEOUT_5M: int = 5 * 60
TIMEOUT_5S: int = 5


async def start() -> None:
    if TASKS:
        return None
    if not TG:
        raise
    channel = CONFIG['youtube_playwright'].get('channel')
    TASKS.append(TG.create_task(YouTube('xxx').main()))
    TASKS.append(TG.create_task(YouTubeStats(channel).main()))


def shutdown() -> None:
    for task in TASKS:
        task.cancel()
    TASKS.clear()
    video_id['video_id'] = ''


class Message(MessageABC):
    id = 'y'


class YouTube(Chat):
    browser: Any
    page: Page
    playwright: Any
    url: str = 'youtube.com'

    async def add_message(self, message: Locator) -> None:
        name = message.locator('#author-name').inner_text()
        text = message.locator('#message').inner_html()
        MESSAGES.append(Message(text=text, name=name))

    async def handle_route(self, route: Route) -> None:
        if route.request.resource_type in ['image', 'stylesheet', 'font', 'xhr'] or \
           self.url not in route.request.url:
            await route.abort()
        else:
            await route.continue_()

    @start_after('video_id', video_id)
    async def main(self) -> None:
        self.channel = video_id['video_id']
        await self.on_start()
        self.add_info()
        await self.start()
        page = self.page
        await page.route('**/*', self.handle_route)
        while True:
            try:
                await page.goto(f'https://www.youtube.com/live_chat?is_popout=1&v={video_id['video_id']}')
                # Все сообщения.
                await page.locator('#trigger.style-scope.tp-yt-paper-menu-button').click()
                await page.locator('a.yt-simple-endpoint.style-scope.yt-dropdown-menu').nth(1).click()
                await asyncio.sleep(TIMEOUT_1S)
                items = page.locator('#items.style-scope.yt-live-chat-item-list-renderer')
                while True:
                    for v in await items.locator('yt-live-chat-text-message-renderer').all():
                        await self.add_message(v)
                    await items.evaluate('(items) => items.innerHTML = ""')
                    self.add_stats()
                    await asyncio.sleep(TIMEOUT_5S)
            except TimeoutError as e:
                self.print_exception(e)
                await asyncio.sleep(TIMEOUT_30S)
            except asyncio.CancelledError:
                await self.on_close()
                raise
            finally:
                await self.browser.close()
                await self.playwright.stop()

    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.firefox.launch(headless=True)
        context = await self.browser.new_context()
        self.page = await context.new_page()

    def add_info(self) -> None:
        text = 'Статистика с YouTube: views, likes.'
        MESSAGES.append(MessageMiranda(text=text))

    def add_stats(self) -> None:
        STATS['y'] = STATS['ys']
