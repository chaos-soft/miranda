from collections.abc import Awaitable, Callable
import asyncio

from google.auth.exceptions import RefreshError  # type: ignore
from google.auth.transport.requests import Request  # type: ignore
from google.oauth2.credentials import Credentials  # type: ignore
from google_auth_oauthlib.flow import Flow  # type: ignore
from googleapiclient import discovery, errors  # type: ignore
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError  # type: ignore

from .chat import Chat, OAuth
from .common import (
    D,
    MESSAGES,
    MessageABC,
    MessageMiranda,
    RESTART_EVENT,
    STATS,
    get_config_file,
    logger,
)
from .config import CONFIG
from .youtube_rss import YouTubeStats

SCOPES: list[str] = ["https://www.googleapis.com/auth/youtube.readonly"]
TIMEOUT_10M: int = 10 * 60
TIMEOUT_30S: int = 30
TIMEOUT_5M: int = 5 * 60


async def start() -> None:
    channel = CONFIG["youtube"].get("channel", "")
    oauth = OAuthYouTube(channel)
    stats = YouTubeStats(channel)
    y = YouTube(channel, oauth, stats)
    if not get_config_file("client_secret.json").exists():
        y.print_error("отсутствует файл client_secret.json.")
        return None
    await asyncio.gather(
        oauth.main(),
        stats.main(),
        y.main(),
        return_exceptions=True,
    )


class Message(MessageABC):
    id = "y"


class OAuthYouTube(Chat):
    credentials: Credentials | None
    credentials_event: asyncio.Event
    file_name: str = "youtube.json"
    flow: Flow
    redirect_uri: str = OAuth.redirect_uri
    state: str = "youtube-xxx"

    def __init__(self, channel: str) -> None:
        super().__init__(channel)
        self.credentials_event = asyncio.Event()
        self.load_credentials()

    async def catch(self, f: Callable[[], Awaitable[None]]) -> None:
        try:
            await f()
        except RefreshError as e:
            get_config_file(self.file_name).unlink()
            logger.exception(e)
            self.log_refresh_error(e)
            self.print_exception(e)
            RESTART_EVENT.set()

    async def get_authorization_url(self) -> None:
        if self.credentials_event.is_set() or CONFIG["youtube"]["code"]:
            return None
        await self.on_start("get_authorization_url()")
        self.get_flow()
        url, self.state = self.flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        text = f'<a href="{url}">Авторизация в YouTube</a>.'
        MESSAGES.append(MessageMiranda(text=text))

    async def get_credentials(self) -> None:
        if self.credentials_event.is_set() or not CONFIG["youtube"]["code"]:
            return None
        await self.on_start("get_credentials()")
        self.get_flow()
        try:
            self.flow.fetch_token(code=CONFIG["youtube"]["code"])
            self.credentials = self.flow.credentials
            self.credentials_event.set()
            self.dump_credentials()
        except InvalidGrantError as e:
            self.print_exception(e)

    async def main(self) -> None:
        await self.catch(self.get_authorization_url)
        await self.catch(self.get_credentials)
        await self.credentials_event.wait()
        asyncio.create_task(self.catch(self.refresh_credentials))

    async def refresh_credentials(self) -> None:
        assert self.credentials is not None
        await self.on_start("refresh_credentials()")
        request = Request()
        while True:
            if not self.credentials.valid:
                self.credentials.refresh(request)
                self.credentials_event.set()
                self.dump_credentials()
            else:
                await asyncio.sleep(TIMEOUT_5M)

    def dump_credentials(self) -> None:
        if not self.credentials:
            return None
        with get_config_file(self.file_name).open("w") as f:
            f.write(self.credentials.to_json())

    def get_flow(self) -> None:
        self.flow = Flow.from_client_secrets_file(
            get_config_file("client_secret.json"),
            redirect_uri=self.redirect_uri,
            scopes=SCOPES,
            state=self.state,
        )

    def load_credentials(self) -> None:
        try:
            self.credentials = Credentials.from_authorized_user_file(
                get_config_file(self.file_name), SCOPES
            )
            if self.credentials.valid:
                self.credentials_event.set()
        except (ValueError, FileNotFoundError):
            self.credentials = None

    def log_refresh_error(self, e: Exception) -> None:
        msg = "RefreshError\ncredentials: {}\ncredentials.valid: {}".format(
            self.credentials,
            self.credentials.valid if self.credentials else None,
        )
        logger.debug(msg)


class YouTube(Chat):
    chat_id: str = ""
    chat_id_event: asyncio.Event
    likes: str = ""
    oauth: OAuthYouTube
    quota: int = 0
    requests: int = 0
    stats: YouTubeStats
    viewers: int = 0
    views: str = ""
    youtube: discovery.Resource

    def __init__(self, channel: str, oauth: OAuthYouTube, stats: YouTubeStats) -> None:
        super().__init__(channel)
        self.chat_id_event = asyncio.Event()
        self.oauth = oauth
        self.stats = stats

    async def get_chat_id(self) -> None:
        request = self.youtube.videos().list(
            part="liveStreamingDetails,statistics", id=self.stats.video_id
        )
        while True:
            try:
                response = request.execute()
                if not response["items"]:
                    self.print_error("нет стримов.")
                elif (
                    "activeLiveChatId"
                    not in response["items"][0]["liveStreamingDetails"]
                ):
                    self.print_error("нет активных стримов.")
                else:
                    self.chat_id = response["items"][0]["liveStreamingDetails"][
                        "activeLiveChatId"
                    ]
                    self.chat_id_event.set()
                    self.likes = response["items"][0]["statistics"]["likeCount"]
                    self.viewers = response["items"][0]["liveStreamingDetails"].get(
                        "concurrentViewers", 0
                    )
                    self.views = response["items"][0]["statistics"]["viewCount"]
                self.add_stats(quota=1)
                await asyncio.sleep(TIMEOUT_10M)
            except errors.HttpError as e:
                if self.process_exception(e):
                    return None
                await asyncio.sleep(TIMEOUT_30S)
            except TimeoutError as e:
                self.process_exception(e)
                await asyncio.sleep(TIMEOUT_30S)
            except RefreshError:
                return None

    async def get_messages(self) -> None:
        request = self.youtube.liveChatMessages().list(
            liveChatId=self.chat_id, part="snippet,authorDetails"
        )
        while True:
            try:
                response = request.execute()
                self.add_stats(quota=5)
                if response["items"]:
                    for v in response["items"]:
                        self.add_message(v)
                request = self.youtube.liveChatMessages().list_next(request, response)
                timeout = response["pollingIntervalMillis"] / 1000
                if timeout < TIMEOUT_30S:
                    timeout = TIMEOUT_30S
                await asyncio.sleep(timeout)
            except errors.HttpError as e:
                if self.process_exception(e):
                    await self.on_close()
                    return None
                await asyncio.sleep(TIMEOUT_30S)
            except TimeoutError as e:
                self.process_exception(e)
                await asyncio.sleep(TIMEOUT_30S)
            except RefreshError:
                return None
            except asyncio.CancelledError:
                await self.on_close()
                raise

    async def main(self) -> None:
        await self.oauth.credentials_event.wait()
        await self.stats.video_id_event.wait()
        self.youtube = discovery.build(
            "youtube", "v3", credentials=self.oauth.credentials
        )
        asyncio.create_task(self.get_chat_id())
        await self.chat_id_event.wait()
        asyncio.create_task(self.get_messages())
        await self.on_start()
        self.add_info()

    def add_info(self) -> None:
        text = "Статистика с YouTube: views, likes, viewers."
        MESSAGES.append(MessageMiranda(text=text))

    def add_message(self, message: D) -> None:
        name = message["authorDetails"]["displayName"]
        text = message["snippet"]["displayMessage"]
        MESSAGES.append(Message(text=text, name=name))

    def add_stats(self, quota: int) -> None:
        self.quota += quota
        self.requests += 1
        STATS["y"] = f"{self.views} {self.likes} {self.viewers}"
        if self.requests % 100 == 0:
            text = (
                "Статистика с YouTube:"
                + f" requests — {self.requests}, quota — {self.quota}."
            )
            MESSAGES.append(MessageMiranda(text=text))

    def process_exception(self, e: Exception) -> bool:
        self.print_exception(e)
        if "quotaExceeded" in str(e):
            return True
        else:
            return False
