from collections.abc import Callable
from typing import Any, Union
import asyncio

from google.auth.exceptions import RefreshError  # type: ignore
from google.auth.transport.requests import Request  # type: ignore
from google.oauth2.credentials import Credentials  # type: ignore
from google_auth_oauthlib.flow import Flow  # type: ignore
from googleapiclient import discovery, errors  # type: ignore
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError  # type: ignore

from .chat import Base
from .common import (
    D,
    MESSAGES,
    MessageABC,
    MessageMiranda,
    STATS,
    T,
    get_config_file,
    logger,
    start_after,
)
from .config import CONFIG
from .youtube_rss import YouTubeStats, video_id

C = Union[Credentials | None]

SCOPES: list[str] = ["https://www.googleapis.com/auth/youtube.readonly"]
TASKS: T = []
TG: asyncio.TaskGroup | None = None
TIMEOUT_10M: int = 10 * 60
TIMEOUT_15S: int = 15
TIMEOUT_30S: int = 30
TIMEOUT_5M: int = 5 * 60

chat_id: str = ""
file_name: str = "youtube.json"


def load_credentials(name: str) -> C:
    try:
        credentials = Credentials.from_authorized_user_file(
            get_config_file(file_name), SCOPES
        )
    except (ValueError, FileNotFoundError):
        credentials = None
    return credentials


credentials: C = load_credentials(file_name)


async def catch(f: Callable) -> None:
    try:
        await f()
    except* RefreshError as e:
        global credentials
        log_refresh_error(e, f.__name__)
        logger.exception(e)
        shutdown()
        get_config_file(file_name).unlink()
        credentials = load_credentials(file_name)
        await start()


async def start() -> None:
    if TASKS:
        shutdown()
    assert TG is not None
    y = YouTube()
    if not get_config_file("client_secret.json").exists():
        y.print_error("отсутствует файл client_secret.json.")
        return None

    channel = CONFIG["youtube"].get("channel")
    o = OAuthYouTube()
    TASKS.append(TG.create_task(catch(o.get_authorization_url)))
    TASKS.append(TG.create_task(catch(o.get_credentials)))
    TASKS.append(TG.create_task(catch(o.refresh_credentials)))
    TASKS.append(TG.create_task(catch(y.get_chat_id)))
    TASKS.append(TG.create_task(catch(y.main)))
    TASKS.append(TG.create_task(catch(YouTubeStats(channel).main)))


def dump_credentials() -> None:
    if not credentials:
        return None
    with get_config_file(file_name).open("w") as f:
        f.write(credentials.to_json())


def log_refresh_error(e: Exception, f: str) -> None:
    msg = "RefreshError\ncredentials: {}\ncredentials.valid: {}\nf: {}".format(
        credentials,
        credentials.valid if credentials else None,
        f,
    )
    logger.debug(msg)


def shutdown() -> None:
    global chat_id
    for task in TASKS:
        task.cancel()
    TASKS.clear()
    chat_id = ""
    video_id["video_id"] = ""


class Commands:
    def set_youtube_video_id(self, command_text: str, **kwargs: Any) -> None:
        video_id["video_id"] = command_text


class Message(MessageABC):
    id = "y"


class OAuthYouTube(Base):
    flow: Flow
    redirect_uri: str = "http://localhost:5173"
    state: str = "youtube-xxx"

    async def get_authorization_url(self) -> None:
        if credentials or CONFIG["youtube"]["code"]:
            return None
        await self.on_start("get_authorization_url")
        await self.get_flow()
        url, self.state = self.flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        text = f'<a href="{url}">Авторизация в YouTube</a>.'
        MESSAGES.append(MessageMiranda(text=text))

    async def get_credentials(self) -> None:
        global credentials
        if credentials is not None or not CONFIG["youtube"]["code"]:
            return None
        await self.on_start("get_credentials")
        await self.get_flow()
        try:
            self.flow.fetch_token(code=CONFIG["youtube"]["code"])
            credentials = self.flow.credentials
            dump_credentials()
        except InvalidGrantError as e:
            self.print_exception(e)

    async def get_flow(self) -> None:
        self.flow = Flow.from_client_secrets_file(
            get_config_file("client_secret.json"),
            redirect_uri=self.redirect_uri,
            scopes=SCOPES,
            state=self.state,
        )

    async def refresh_credentials(self) -> None:
        global credentials
        await self.on_start("refresh_credentials")
        request = Request()
        while True:
            if credentials and not credentials.valid:
                credentials.refresh(request)
                dump_credentials()
            await asyncio.sleep(TIMEOUT_5M)


class YouTube(Base):
    likes: str = ""
    quota: int = 0
    requests: int = 0
    viewers: int = 0
    views: str = ""
    youtube: discovery.Resource

    @start_after("credentials", globals())
    @start_after("video_id", video_id)
    async def get_chat_id(self) -> None:
        global chat_id
        self.youtube = discovery.build("youtube", "v3", credentials=credentials)
        request = self.youtube.videos().list(
            part="liveStreamingDetails,statistics", id=video_id["video_id"]
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
                    chat_id = response["items"][0]["liveStreamingDetails"][
                        "activeLiveChatId"
                    ]
                    self.likes = response["items"][0]["statistics"]["likeCount"]
                    self.viewers = response["items"][0]["liveStreamingDetails"].get(
                        "concurrentViewers", 0
                    )
                    self.views = response["items"][0]["statistics"]["viewCount"]
                self.add_stats(quota=1)
                await asyncio.sleep(TIMEOUT_10M)
            except errors.HttpError as e:
                if self.process_exception(e):
                    await self.on_close()
                    return None
                await asyncio.sleep(TIMEOUT_30S)
            except RefreshError as e:
                log_refresh_error(e, "get_chat_id")
                await asyncio.sleep(TIMEOUT_30S)
            except TimeoutError as e:
                self.process_exception(e)
                return None

    @start_after("chat_id", globals())
    async def main(self) -> None:
        self.channel = video_id["video_id"]
        await self.on_start()
        self.add_info()
        request = self.youtube.liveChatMessages().list(
            liveChatId=chat_id, part="snippet,authorDetails"
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
                if timeout < TIMEOUT_15S:
                    timeout = TIMEOUT_15S
                await asyncio.sleep(timeout)
            except errors.HttpError as e:
                if self.process_exception(e):
                    await self.on_close()
                    return None
                await asyncio.sleep(TIMEOUT_30S)
            except RefreshError as e:
                log_refresh_error(e, "main")
                await asyncio.sleep(TIMEOUT_30S)
            except asyncio.CancelledError:
                await self.on_close()
                raise

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
