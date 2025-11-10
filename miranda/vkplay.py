from base64 import standard_b64encode
from urllib.parse import quote_plus
import asyncio
import json

from .chat import Chat, WebSocket
from .common import (
    D,
    dump_credentials,
    load_credentials,
    make_request,
    MessageABC,
    MessageMiranda,
    MESSAGES,
    start_after,
    STATS,
    T,
)
from .config import CONFIG

CLIENT_ID: str = '534nwhjhsn894my7'
CLIENT_SECRET: str = 'DjTki7eQbDA7hfSLH9znrhmdanq6lRFXbsMIHF5k2nkw5OobkVHy4eQITZmYYqcG'
TASKS: T = []
TG: asyncio.TaskGroup | None = None
TIMEOUT_1M: int = 1 * 60
TIMEOUT_30S: int = 30
TIMEOUT_30SF: float = 30.0

channel_id: int = 0
chat_token: str = ''
file_name: str = 'vkplay.json'
is_refresh_credentials: bool = False
credentials: dict[str, str] = load_credentials(file_name)


@start_after('credentials', globals())
async def get_chat_token() -> None:
    global chat_token
    url = 'https://apidev.live.vkvideo.ru/v1/websocket/token'
    while True:
        data = await make_request(url, timeout=TIMEOUT_30SF, headers=get_headers())
        if data:
            chat_token = data['data']['token']
            return None
        else:
            await OAuth.refresh_credentials()


async def start() -> None:
    if TASKS:
        return None
    if not TG:
        raise
    channel = CONFIG['vkplay'].get('channel')
    TASKS.append(TG.create_task(get_chat_token()))
    TASKS.append(TG.create_task(OAuth.get_authorization_url()))
    TASKS.append(TG.create_task(OAuth.get_credentials()))
    TASKS.append(TG.create_task(VK(channel).main()))
    TASKS.append(TG.create_task(VKStats(channel).main()))


def get_headers() -> dict[str, str]:
    return {'Authorization': f'Bearer {credentials['access_token']}'}


def shutdown() -> None:
    for task in TASKS:
        task.cancel()
    TASKS.clear()


class Message(MessageABC):
    id = 'v'


class OAuth():
    authorization: str = standard_b64encode(':'.join([CLIENT_ID, CLIENT_SECRET]).encode('utf-8')).decode('utf-8')
    authorization_url: str = 'https://auth.live.vkvideo.ru/app/oauth2/authorize'
    redirect_uri: str = 'http://localhost:5173'
    state: str = 'vkplay-xxx'
    token_url: str = 'https://api.live.vkvideo.ru/oauth/server/token'
    headers: dict[str, str] = {
        'Authorization': f'Basic {authorization}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    @classmethod
    async def get_authorization_url(cls) -> None:
        if credentials or CONFIG['vkplay']['code']:
            return None
        print('vkplay_get_authorization_url')
        url = ''.join([
            cls.authorization_url,
            '?response_type=code',
            '&client_id=', CLIENT_ID,
            '&redirect_uri=', quote_plus(cls.redirect_uri),
            '&state=', cls.state,
        ])
        text = f'<a href="{url}">Авторизация в VK</a>.'
        MESSAGES.append(MessageMiranda(text=text))

    @classmethod
    async def get_credentials(cls) -> None:
        global credentials
        if credentials or not CONFIG['vkplay']['code']:
            return None
        print('vkplay_get_credentials')
        while True:
            data = {
                'code': CONFIG['vkplay']['code'],
                'grant_type': 'authorization_code',
                'redirect_uri': cls.redirect_uri,
            }
            d = await make_request(cls.token_url, timeout=TIMEOUT_30SF, method='POST', data=data, headers=cls.headers)
            if d:
                credentials = d
                dump_credentials(file_name, credentials)
                return None
            await asyncio.sleep(TIMEOUT_30S)

    @classmethod
    async def refresh_credentials(cls) -> None:
        global credentials, is_refresh_credentials
        if is_refresh_credentials:
            await asyncio.sleep(TIMEOUT_30S)
            return None
        is_refresh_credentials = True
        print('vkplay_refresh_credentials')
        data = {
            'grant_type': 'refresh_token',
            'redirect_uri': cls.redirect_uri,
            'refresh_token': credentials['refresh_token'],
        }
        data = await make_request(cls.token_url, timeout=TIMEOUT_30SF, method='POST', data=data, headers=cls.headers)
        if data:
            credentials = data
            dump_credentials(file_name, credentials)
        is_refresh_credentials = False


class VK(WebSocket):
    url: str = 'wss://pubsub-dev.live.vkvideo.ru/connection/websocket?format=json&cf_protocol_version=v2'

    @start_after(['chat_token', 'channel_id'], globals())
    async def main(self) -> None:
        await super().main()

    async def on_message(self, data_str: str) -> None:
        if data_str == '{}':
            await self.w.send(data_str)
            return None

        for v in data_str.split('\n'):
            data = json.loads(v)
            if 'connect' in data:
                data = '{"subscribe":{"channel":"channel-chat:{}"},"id":2}'
                await self.w.send(data.replace('{}', str(channel_id)))
            elif 'push' in data:
                if data['push']['pub']['data']['type'] == 'delete_message':
                    pass
                elif data['push']['pub']['data']['type'] == 'message':
                    self.add_message(data['push']['pub']['data']['data'])
                else:
                    print('tmp_grep push', data)
            else:
                print('tmp_grep else', data)

    async def on_open(self) -> None:
        data = {
            'connect': {
                'token': chat_token,
                'name': 'js',
            },
            'id': 1,
        }
        await self.w.send(json.dumps(data))

    def add_message(self, message: D) -> None:
        images: D = {}
        name = message['user']['displayName']
        text = []
        for i, v in enumerate(message['data']):
            if v['type'] in ['text', 'link'] and v['content']:
                content = json.loads(v['content'])
                text.append(content[0])
            elif v['type'] == 'smile':
                k = f':{i}:'
                images[k] = v['largeUrl']
                text.append(k)
            elif v['type'] == 'mention':
                text.append(v['displayName'])
        MESSAGES.append(Message(text=' '.join(text), name=name, images=images))


class VKStats(Chat):
    url: str = 'https://apidev.live.vkvideo.ru/v1/channel?channel_url={}'

    async def load(self) -> None:
        global channel_id
        data = await make_request(self.url, timeout=TIMEOUT_30SF, headers=get_headers())
        if data:
            channel_id = data['data']['channel']['id']
            self.alert(data['data']['stream']) if data['data']['stream'] else None
        else:
            await OAuth.refresh_credentials()

    @start_after('credentials', globals())
    async def main(self) -> None:
        await self.on_start()
        self.add_info()
        self.url = self.url.format(self.channel)
        try:
            while True:
                await self.load()
                await asyncio.sleep(TIMEOUT_1M)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    def add_info(self) -> None:
        text = 'Статистика с VK: views, reactions, viewers.'
        MESSAGES.append(MessageMiranda(text=text))

    def alert(self, data: D) -> None:
        views: int = data['counters']['views']
        reactions: int = sum(map(lambda r: r['count'], data['reactions']))
        viewers: int = data['counters']['viewers']
        STATS['v'] = f'{views} {reactions} {viewers}'
