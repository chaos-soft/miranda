from datetime import datetime
from urllib.parse import quote_plus
import asyncio

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

CLIENT_ID: str = 'g0qvsrztagks1lbg03kwnt67pg9x8a5'
CLIENT_SECRET: str = 'krlzbgo35j454d6aoxemjmnjifeoi9'
FOLLOWS: dict[str, int] = {}
SCOPES: list[str] = ['chat:read', 'moderator:read:followers']
TASKS: T = []
TG: asyncio.TaskGroup | None = None
TIMEOUT_10S: int = 10
TIMEOUT_30S: int = 30
TIMEOUT_30SF: float = 30.0
TIMEOUT_5M: int = 5 * 60

channel_id: str = ''
file_name: str = 'twitch.json'
is_refresh_credentials: bool = False
credentials: dict[str, str] = load_credentials(file_name)


@start_after('credentials', globals())
async def get_channel_id(channel: str) -> None:
    global channel_id
    # https://dev.twitch.tv/docs/api/reference/#get-users
    url = f'https://api.twitch.tv/helix/users?login={channel}'
    while True:
        data = await make_request(url, timeout=TIMEOUT_30SF, headers=get_headers())
        if data:
            channel_id = data['data'][0]['id']
            return None
        else:
            await OAuth.refresh_credentials()


async def start() -> None:
    if TASKS:
        return None
    if not TG:
        raise
    channels = CONFIG['twitch'].getlist('channels')
    for channel in channels:
        TASKS.append(TG.create_task(Twitch(channel).main()))
        if channels.index(channel) == 0:
            if CONFIG['twitch'].getboolean('is_follows'):
                TASKS.append(TG.create_task(TwitchFollows(channel).main()))
            if CONFIG['twitch'].getboolean('is_stats'):
                TASKS.append(TG.create_task(TwitchStats(channel).main()))
            if CONFIG['twitch'].getboolean('is_follows') or CONFIG['twitch'].getboolean('is_stats'):
                TASKS.append(TG.create_task(get_channel_id(channel)))
                TASKS.append(TG.create_task(OAuth.get_authorization_url()))
                TASKS.append(TG.create_task(OAuth.get_credentials()))


def get_headers() -> dict[str, str]:
    return {'Client-ID': CLIENT_ID, 'Authorization': f'Bearer {credentials['access_token']}'}


def shutdown() -> None:
    for task in TASKS:
        task.cancel()
    TASKS.clear()


class Message(MessageABC):
    color: str
    id = 't'
    timestamp: int = 0

    def to_dict(self) -> D:
        d = super().to_dict()
        d['color'] = self.color
        return d


class OAuth():
    authorization_url: str = 'https://id.twitch.tv/oauth2/authorize'
    redirect_uri: str = 'http://localhost:5173'
    state: str = 'twitch-xxx'
    token_url: str = 'https://id.twitch.tv/oauth2/token'

    @classmethod
    async def get_authorization_url(cls) -> None:
        if credentials or CONFIG['twitch']['code']:
            return None
        print('twitch_get_authorization_url')
        url = ''.join([
            cls.authorization_url,
            '?response_type=code',
            '&client_id=', CLIENT_ID,
            '&redirect_uri=', quote_plus(cls.redirect_uri),
            '&scope=', quote_plus(' '.join(SCOPES)),
            '&state=', cls.state,
        ])
        text = f'<a href="{url}">Авторизация в Twitch</a>.'
        MESSAGES.append(MessageMiranda(text=text))

    @classmethod
    async def get_credentials(cls) -> None:
        global credentials
        if credentials or not CONFIG['twitch']['code']:
            return None
        print('twitch_get_credentials')
        while True:
            data = {
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'code': CONFIG['twitch']['code'],
                'grant_type': 'authorization_code',
                'redirect_uri': cls.redirect_uri,
            }
            d = await make_request(cls.token_url, timeout=TIMEOUT_30SF, method='POST', data=data)
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
        print('twitch_refresh_credentials')
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': credentials['refresh_token'],
        }
        data = await make_request(cls.token_url, timeout=TIMEOUT_30SF, method='POST', data=data)
        if data:
            credentials = data
            dump_credentials(file_name, credentials)
        is_refresh_credentials = False


class Twitch(WebSocket):
    keys: list[str] = ['color', 'emotes', 'display-name', 'user-id', 'system-msg']
    url: str = 'wss://irc-ws.chat.twitch.tv'

    @start_after('credentials', globals())
    async def main(self) -> None:
        await super().main()

    async def on_message(self, data: str) -> None:
        if 'PRIVMSG' in data:
            self.add_message(self.parse_data(data))
        elif 'USERNOTICE' in data:
            self.add_notify(self.parse_data(data))
        elif data.startswith('PING'):
            await self.send_pong(data)

    async def on_open(self) -> None:
        # PASS и NICK именно в таком порядке.
        await self.w.send(f'PASS oauth:{credentials['access_token']}\r\n')
        await self.w.send('NICK chaos-soft\r\n')
        await self.w.send('CAP REQ :twitch.tv/tags twitch.tv/commands\r\n')
        await self.w.send(f'JOIN #{self.channel}\r\n')

    async def send_pong(self, data: str) -> None:
        await self.w.send(f'{data.replace("PING", "PONG")}\r\n')

    def add_message(self, message: D) -> None:
        if message['user-id'] in FOLLOWS:
            message['timestamp'] = FOLLOWS[message['user-id']]
        message.pop('user-id')
        message['name'] = message.pop('display-name')
        self.parse_emotes(message)
        MESSAGES.append(Message(**message))

    def add_notify(self, message: D) -> None:
        text = CONFIG['twitch']['text'].format(message['system-msg'].replace(r'\s', ' '))
        MESSAGES.append(MessageMiranda(text=text, is_event=True))

    def clean_text(self, text: str) -> str:
        """Очищает от /me."""
        return text[8:-1] if text.startswith('\x01') else text

    def parse_data(self, data: str) -> D:
        parts = data.split(' ', 4)
        message = {}
        if len(parts) == 5:
            message['text'] = self.clean_text(parts[4][1:])
        for part in parts[0].split(';'):
            k, v = part.split('=')
            if v and k in self.keys:
                message[k] = v
        return message

    def parse_emotes(self, message: D) -> None:
        if 'emotes' not in message:
            return None
        images = {}
        for emote in message['emotes'].split('/'):
            id, indexes = emote.split(':')
            indexes = indexes.split(',', 1)[0].split('-')
            k = message['text'][int(indexes[0]):int(indexes[1]) + 1]
            images[k] = f'https://static-cdn.jtvnw.net/emoticons/v2/{id}/static/light/3.0'
        message.pop('emotes')
        message['images'] = dict(sorted(images.items(), key=lambda v: len(v[0]), reverse=True))


class TwitchFollows(Chat):
    is_first_run: bool = True
    params: D = {'first': 100, 'broadcaster_id': None}
    # https://dev.twitch.tv/docs/api/reference/#get-channel-followers
    url: str = 'https://api.twitch.tv/helix/channels/followers'

    async def load(self) -> int:
        data = await make_request(self.url, params=self.params, timeout=TIMEOUT_30SF, headers=get_headers())
        if not data:
            await OAuth.refresh_credentials()
            return TIMEOUT_10S
        for follow in data['data']:
            if follow['user_id'] in FOLLOWS:
                break
            FOLLOWS[follow['user_id']] = int(
                datetime.strptime(follow['followed_at'].split('T')[0], '%Y-%m-%d').timestamp(),
            )
            if not self.is_first_run:
                self.alert(follow)
        if not self.is_first_run:
            return TIMEOUT_5M

        if len(FOLLOWS) < CONFIG['twitch'].getint('follows_limit') and len(FOLLOWS) != data['total']:
            self.params['after'] = data['pagination']['cursor']
            return TIMEOUT_10S
        else:
            self.params.pop('after', None)
            self.params['first'] = 10
            self.is_first_run = False
            self.print_error(f'запущен ({data['total']}).')
            return TIMEOUT_5M

    @start_after(['credentials', 'channel_id'], globals())
    async def main(self) -> None:
        await self.on_start()
        self.params['broadcaster_id'] = channel_id
        if self.params['first'] > CONFIG['twitch'].getint('follows_limit'):
            self.params['first'] = CONFIG['twitch'].getint('follows_limit')
        try:
            while True:
                sleep = await self.load()
                await asyncio.sleep(sleep)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    def alert(self, follow: dict[str, str]) -> None:
        text = CONFIG['twitch']['text_follower'].format(follow['user_name'] or follow['user_login'])
        MESSAGES.append(MessageMiranda(text=text, is_event=True))


class TwitchStats(Chat):
    url: str = 'https://api.twitch.tv/helix/streams?user_login={}&first=1'

    async def load(self) -> None:
        data = await make_request(self.url, timeout=TIMEOUT_30SF, headers=get_headers())
        if data:
            self.alert(data['data'][0]['viewer_count'] if data['data'] else '')
        else:
            await OAuth.refresh_credentials()

    @start_after('credentials', globals())
    async def main(self) -> None:
        await self.on_start()
        self.url = self.url.format(self.channel)
        try:
            while True:
                await self.load()
                await asyncio.sleep(TIMEOUT_30S)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    def alert(self, v: str) -> None:
        STATS['t'] = v
