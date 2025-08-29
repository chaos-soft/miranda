import asyncio

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient import discovery, errors

from .chat import Base
from .common import MESSAGES, D, get_config_file, STATS, start_after, T
from .config import CONFIG
from .youtube_rss import YouTubeStats, video_id

SCOPES: list[str] = ['https://www.googleapis.com/auth/youtube.readonly']
TASKS: T = []
TG: asyncio.TaskGroup | None = None
TIMEOUT_10M: int = 10 * 60
TIMEOUT_15S: int = 15
TIMEOUT_30S: int = 30
TIMEOUT_5M: int = 5 * 60

chat_id: str = ''
credentials: Credentials | None
file_name: str = 'youtube.json'
try:
    credentials = Credentials.from_authorized_user_file(get_config_file(file_name), SCOPES)
except (ValueError, FileNotFoundError):
    credentials = None


async def start() -> None:
    if TASKS:
        return None
    if not TG:
        raise
    channel = CONFIG['youtube'].get('channel')
    y = YouTube()
    TASKS.append(TG.create_task(OAuth.get_authorization_url()))
    TASKS.append(TG.create_task(OAuth.get_credentials()))
    TASKS.append(TG.create_task(OAuth.refresh_credentials()))
    TASKS.append(TG.create_task(y.get_chat_id()))
    TASKS.append(TG.create_task(y.main()))
    TASKS.append(TG.create_task(YouTubeStats(channel).main()))


def dump_credentials() -> None:
    if not credentials:
        return None
    with get_config_file(file_name).open('w') as f:
        f.write(credentials.to_json())


def shutdown() -> None:
    for task in TASKS:
        task.cancel()
    TASKS.clear()


class OAuth():
    flow: Flow
    redirect_uri: str = 'http://localhost:5173'
    state: str = 'youtube-xxx'

    @classmethod
    async def get_authorization_url(cls) -> None:
        if credentials or CONFIG['youtube']['code']:
            return None
        print('youtube_get_authorization_url')
        await cls.get_flow()
        url, cls.state = cls.flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
        )
        MESSAGES.append(dict(id='m', text=f'<a href="{url}">Авторизация в YouTube</a>.'))

    @classmethod
    async def get_credentials(cls) -> None:
        global credentials
        if credentials is not None or not CONFIG['youtube']['code']:
            return None
        print('youtube_get_credentials')
        await cls.get_flow()
        cls.flow.fetch_token(code=CONFIG['youtube']['code'])
        credentials = cls.flow.credentials
        dump_credentials()

    @classmethod
    async def get_flow(cls) -> None:
        cls.flow = Flow.from_client_secrets_file(
            get_config_file('client_secret.json'),
            scopes=SCOPES,
            state=cls.state,
        )
        cls.flow.redirect_uri = cls.redirect_uri

    @classmethod
    async def refresh_credentials(cls) -> None:
        print('youtube_refresh_credentials')
        request = Request()
        while True:
            if credentials and not credentials.valid:
                credentials.refresh(request)
                dump_credentials()
            await asyncio.sleep(TIMEOUT_5M)


class YouTube(Base):
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
                if response['items']:
                    chat_id = response['items'][0]['liveStreamingDetails']['activeLiveChatId']
                    self.likes = response['items'][0]['statistics']['likeCount']
                    self.viewers = response['items'][0]['liveStreamingDetails'].get('concurrentViewers', 0)
                    self.views = response['items'][0]['statistics']['viewCount']
                else:
                    await self.print_error('нет стримов.')
                self.add_stats(quota=1)
                await asyncio.sleep(TIMEOUT_10M)
            except errors.HttpError as e:
                await self.print_exception(e)
                await asyncio.sleep(TIMEOUT_30S)

    @start_after('chat_id', globals())
    async def main(self) -> None:
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
                await self.print_exception(e)
                await asyncio.sleep(TIMEOUT_30S)
            except asyncio.CancelledError:
                await self.on_close()
                raise

    def add_info(self) -> None:
        MESSAGES.append(
            dict(id='m', text='Статистика с YouTube: views, likes, viewers, requests, quota.'),
        )

    def add_message(self, message: D) -> None:
        MESSAGES.append(
            dict(id='y', text=message['snippet']['displayMessage'], name=message['authorDetails']['displayName']),
        )

    def add_stats(self, quota: int) -> None:
        self.quota += quota
        self.requests += 1
        STATS['y'] = f'{self.views} {self.likes} {self.viewers} {self.requests} {self.quota}'
