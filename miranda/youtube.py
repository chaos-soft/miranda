from typing import Union
import asyncio

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient import discovery, errors
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from .chat import Base, Chat
from .common import MESSAGES, D, get_config_file, STATS, start_after, T
from .config import CONFIG
from .youtube_rss import YouTubeStats, video_id

C = Union[Credentials | None]
SCOPES: list[str] = ['https://www.googleapis.com/auth/youtube.readonly']
TASKS: T = []
TG: asyncio.TaskGroup | None = None
TIMEOUT_10M: int = 10 * 60
TIMEOUT_15S: int = 15
TIMEOUT_30S: int = 30
TIMEOUT_5M: int = 5 * 60

chat_id: str = ''
file_name: str = 'youtube.json'


def load_credentials(name: str) -> C:
    try:
        credentials = Credentials.from_authorized_user_file(get_config_file(file_name), SCOPES)
    except (ValueError, FileNotFoundError):
        credentials = None
    return credentials


credentials: C = load_credentials(file_name)


async def catch(f) -> None:
    try:
        await f()
    except* RefreshError:
        global credentials
        shutdown()
        get_config_file(file_name).unlink()
        credentials = load_credentials(file_name)
        await start()


async def start() -> None:
    if TASKS:
        return None
    if not TG:
        raise
    channel = CONFIG['youtube'].get('channel')
    o = OAuthYouTube()
    y = YouTube('xxx')
    TASKS.append(TG.create_task(catch(o.get_authorization_url)))
    TASKS.append(TG.create_task(catch(o.get_credentials)))
    TASKS.append(TG.create_task(catch(y.get_chat_id)))
    TASKS.append(TG.create_task(catch(y.main)))
    TASKS.append(TG.create_task(catch(YouTubeStats(channel).main)))


def dump_credentials() -> None:
    if not credentials:
        return None
    with get_config_file(file_name).open('w') as f:
        f.write(credentials.to_json())


def shutdown() -> None:
    global chat_id
    for task in TASKS:
        task.cancel()
    TASKS.clear()
    chat_id = ''
    video_id['video_id'] = ''


class OAuthYouTube(Base):
    flow: Flow
    redirect_uri: str = 'http://localhost:5173'
    state: str = 'youtube-xxx'

    async def get_authorization_url(self) -> None:
        if credentials or CONFIG['youtube']['code']:
            return None
        await self.on_start('get_authorization_url')
        await self.get_flow()
        url, self.state = self.flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
        )
        MESSAGES.append(dict(id='m', text=f'<a href="{url}">Авторизация в YouTube</a>.'))

    async def get_credentials(self) -> None:
        global credentials
        if credentials is not None or not CONFIG['youtube']['code']:
            return None
        await self.on_start('get_credentials')
        await self.get_flow()
        try:
            self.flow.fetch_token(code=CONFIG['youtube']['code'])
            credentials = self.flow.credentials
            dump_credentials()
        except InvalidGrantError as e:
            self.print_exception(e)

    async def get_flow(self) -> None:
        self.flow = Flow.from_client_secrets_file(
            get_config_file('client_secret.json'),
            scopes=SCOPES,
            state=self.state,
        )
        self.flow.redirect_uri = self.redirect_uri

    async def refresh_credentials(self) -> None:
        global credentials
        await self.on_start('refresh_credentials')
        request = Request()
        while True:
            if credentials and not credentials.valid:
                credentials.refresh(request)
                dump_credentials()
            await asyncio.sleep(TIMEOUT_5M)


class YouTube(Chat):
    likes: str = ''
    quota: int = 0
    requests: int = 0
    viewers: int = 0
    views: str = ''
    youtube: discovery.Resource

    @start_after('credentials', globals())
    @start_after('video_id', video_id)
    async def get_chat_id(self) -> None:
        global chat_id
        self.youtube = discovery.build('youtube', 'v3', credentials=credentials)
        request = self.youtube.videos().list(part='liveStreamingDetails,statistics', id=video_id['video_id'])
        while True:
            try:
                response = request.execute()
                if not response['items']:
                    self.print_error('нет стримов.')
                elif 'activeLiveChatId' not in response['items'][0]['liveStreamingDetails']:
                    self.print_error('нет активных стримов.')
                else:
                    chat_id = response['items'][0]['liveStreamingDetails']['activeLiveChatId']
                    self.likes = response['items'][0]['statistics']['likeCount']
                    self.viewers = response['items'][0]['liveStreamingDetails'].get('concurrentViewers', 0)
                    self.views = response['items'][0]['statistics']['viewCount']
                self.add_stats(quota=1)
                await asyncio.sleep(TIMEOUT_10M)
            except errors.HttpError as e:
                if self.process_exception(e):
                    return None
                await asyncio.sleep(TIMEOUT_30S)

    @start_after('chat_id', globals())
    async def main(self) -> None:
        self.channel = video_id['video_id']
        await self.on_start()
        self.add_info()
        request = self.youtube.liveChatMessages().list(liveChatId=chat_id, part='snippet,authorDetails')
        while True:
            try:
                response = request.execute()
                self.add_stats(quota=5)
                if response['items']:
                    for v in response['items']:
                        self.add_message(v)
                request = self.youtube.liveChatMessages().list_next(request, response)
                timeout = response['pollingIntervalMillis'] / 1000
                if timeout < TIMEOUT_15S:
                    timeout = TIMEOUT_15S
                await asyncio.sleep(timeout)
            except errors.HttpError as e:
                if self.process_exception(e):
                    return None
                await asyncio.sleep(TIMEOUT_30S)
            except asyncio.CancelledError:
                await self.on_close()
                raise

    def add_info(self) -> None:
        MESSAGES.append(
            dict(id='m', text='Статистика с YouTube: views, likes, viewers.'),
        )

    def add_message(self, message: D) -> None:
        MESSAGES.append(
            dict(id='y', text=message['snippet']['displayMessage'], name=message['authorDetails']['displayName']),
        )

    def add_stats(self, quota: int) -> None:
        self.quota += quota
        self.requests += 1
        STATS['y'] = f'{self.views} {self.likes} {self.viewers}'
        if self.requests % 100 == 0:
            MESSAGES.append(
                dict(id='m', text=f'Статистика с YouTube: requests — {self.requests}, quota — {self.quota}.'),
            )

    def process_exception(self, e: Exception) -> bool:
        self.print_exception(e)
        if 'quotaExceeded' in str(e):
            return True
        else:
            return False
