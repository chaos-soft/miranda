import asyncio

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient import discovery, errors

from .chat import Base
from .common import MESSAGES, D
from .config import CONFIG, get_config_file

SCOPES: list[str] = ['https://www.googleapis.com/auth/youtube.readonly']
TIMEOUT_10S: int = 10
TIMEOUT_5M: int = 5 * 60

credentials: Credentials | None
try:
    credentials = Credentials.from_authorized_user_file(get_config_file('youtube.json'), SCOPES)
except FileNotFoundError:
    credentials = None
state: str | None = None


async def get_flow() -> Flow:
    flow = Flow.from_client_secrets_file(
        get_config_file('client_secret.json'),
        scopes=SCOPES,
        state=state,
    )
    flow.redirect_uri = 'http://localhost:5173/#/main'
    return flow


async def get_authorization_url() -> None:
    if not credentials:
        print('youtube_get_authorization_url')
        flow = await get_flow()
        global state
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
        )
        MESSAGES.append(dict(id='m', text=f'<a href="{authorization_url}">Авторизация в YouTube</a>.'))


async def get_credentials() -> None:
    global credentials
    if not credentials:
        print('youtube_get_credentials')
        while True:
            if CONFIG['youtube']['code']:
                flow = await get_flow()
                flow.fetch_token(code=CONFIG['youtube']['code'])
                credentials = flow.credentials
                with get_config_file('youtube.json').open('w') as f:
                    f.write(credentials.to_json())
                break
            await asyncio.sleep(TIMEOUT_10S)


async def refresh_credentials() -> None:
    print('youtube_refresh_credentials')
    request = Request()
    while True:
        if credentials and not credentials.valid:
            credentials.refresh(request)
            with get_config_file('youtube.json').open('w') as f:
                f.write(credentials.to_json())
        await asyncio.sleep(TIMEOUT_5M)


class YouTube(Base):
    async def add_message(self, message: D) -> None:
        MESSAGES.append(
            dict(id='y', text=message['snippet']['displayMessage'], name=message['authorDetails']['displayName']),
        )

    async def main(self) -> None:
        try:
            while True:
                if not credentials or not credentials.valid:
                    await asyncio.sleep(TIMEOUT_10S)
                    continue

                youtube = discovery.build('youtube', 'v3', credentials=credentials)
                while True:
                    try:
                        response = youtube.liveBroadcasts().list(part='snippet', broadcastStatus='active').execute()
                        if not response['items']:
                            await self.print_error('нет активных стримов')
                            await asyncio.sleep(TIMEOUT_5M)
                            continue

                        await self.on_start()
                        chat_id = response['items'][0]['snippet']['liveChatId']
                        request = youtube.liveChatMessages().list(liveChatId=chat_id, part='snippet,authorDetails')
                        while True:
                            response = request.execute()
                            if response['items']:
                                for v in response['items']:
                                    await self.add_message(v)
                            request = youtube.liveChatMessages().list_next(request, response)
                            timeout = response['pollingIntervalMillis'] / 1000
                            if timeout < 5:
                                timeout = 5
                            await asyncio.sleep(timeout)
                    except errors.HttpError as e:
                        await self.print_error(e.reason)
                        return None
        except asyncio.CancelledError:
            await self.on_close()
            raise
