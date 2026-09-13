import asyncio

from .chat import Chat
from .common import make_request, STATS

TIMEOUT_5M: int = 5 * 60


class YouTubeStats(Chat):
    """Статистика лайков и просмотров из RSS."""

    url: str = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
    video_id: str = ""
    video_id_event: asyncio.Event

    def __init__(self, channel: str) -> None:
        super().__init__(channel)
        self.url = self.url.format(channel)
        self.video_id_event = asyncio.Event()

    async def load(self) -> None:
        data = await make_request(self.url, is_json=False)
        if data:
            self.add_stats(data)

    async def main(self) -> None:
        await self.on_start()
        try:
            while True:
                await self.load()
                await asyncio.sleep(TIMEOUT_5M)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    def add_stats(self, data: str) -> None:
        views = ""
        likes = ""
        for v in data.split("\n", 50):
            if "<yt:videoId>" in v:
                self.video_id = v.split(">")[1].split("<")[0]
                self.video_id_event.set()
            if "<media:starRating count" in v:
                likes = v.split('"')[1]
            if "<media:statistics views" in v:
                views = v.split('"')[1]
                STATS["ys"] = f"{views} {likes}"
                break
