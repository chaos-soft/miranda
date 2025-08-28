import asyncio

from .chat import Chat
from .common import make_request, STATS, T, D

TASKS: T = []
TG: asyncio.TaskGroup | None = None
TIMEOUT_30SF: float = 30.0
TIMEOUT_5M: int = 5 * 60

video_id: D = dict(video_id='')


class YouTubeStats(Chat):
    """Статистика лайков и просмотров из RSS."""
    url: str = 'https://www.youtube.com/feeds/videos.xml?channel_id={}'

    async def add_stats(self, data: str) -> None:
        views = ''
        likes = ''
        for v in data.split('\n', 50):
            if '<yt:videoId>' in v:
                video_id['video_id'] = v.split('>')[1].split('<')[0]
            if '<media:starRating count' in v:
                likes = v.split('"')[1]
            if '<media:statistics views' in v:
                views = v.split('"')[1]
                STATS['ys'] = f'{views} {likes}'
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
