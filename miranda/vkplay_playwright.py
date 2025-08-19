from typing import Any
import asyncio

from playwright._impl._errors import TimeoutError
from playwright.async_api import Locator, Page, WebSocket, async_playwright

from .chat import Chat
from .common import MESSAGES, STATS
from .config import CONFIG

TASKS: list[asyncio.Task[None]] = []
TG: asyncio.TaskGroup | None = None
TIMEOUT_1S: int = 1


async def start() -> None:
    if 'vkplay_playwright' not in CONFIG or TASKS:
        return None
    if not TG:
        raise
    channel = CONFIG['vkplay_playwright'].get('channel')
    TASKS.append(TG.create_task(VKPlay(channel).main()))


def shutdown() -> None:
    for task in TASKS:
        task.cancel()
    STATS['v'] = ''


class VKPlay(Chat):
    browser: Any
    is_push: bool = True
    page: Page
    playwright: Any
    url: str = 'vkvideo.ru'

    async def add_message(self, message: Locator) -> None:
        name = await message.locator('[data-role=messageAuthor]').inner_text()
        MESSAGES.extend([dict(
            id='v',
            name=name.rstrip(':'),
            text=await message.locator('[data-role=markup]').inner_html(),
        )])

    async def add_stats(self, stats: Locator) -> None:
        if await stats.count():
            STATS['v'] = await stats.inner_text()
        else:
            STATS['v'] = ''

    async def main(self) -> None:
        await self.start()
        try:
            page = self.page
            await page.route('**/*', self.handle_route)
            page.on('websocket', self.on_websocket)
            await page.goto(f'https://live.vkvideo.ru/{self.channel}/only-chat')
            await self.on_start()
            items = page.locator('data-test-id=ChatMessage:root')
            stats = page.locator('xpath=/html/body/div[1]/div/div/div/div/div[2]/div[1]/div[1]/div/div/span')
            while True:
                if self.is_push:
                    self.is_push = False
                    for v in await items.all():
                        await self.add_message(v)
                    while await items.count():
                        v = items.first
                        await v.evaluate('(v) => v.parentElement.remove()')
                await self.add_stats(stats)
                await asyncio.sleep(TIMEOUT_1S)
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

    def on_message(self, data: str | bytes):
        if str(data).startswith('{"push":'):
            self.is_push = True

    def on_websocket(self, w: WebSocket) -> None:
        w.on('framereceived', self.on_message)
