from datetime import datetime
from urllib.parse import quote_plus
import asyncio
import json

from .chat import Chat, WebSocket
from .common import make_request, MESSAGES, STATS, D
from .config import CONFIG, get_config_file

CLIENT_ID: str = 'l0sytxv7tot9ynjakkx4o6ddlpn6qp'
CLIENT_SECRET: str = 'ba1c1wg5b40l9a8ed2ha81edoeh13o'
FOLLOWS: dict[str, int] = {}
SCOPES: list[str] = ['chat:read', 'moderator:read:followers']
TIMEOUT_10S: int = 10
TIMEOUT_30S: int = 30
TIMEOUT_30SF: float = 30.0
TIMEOUT_5M: int = 5 * 60

channel_id: str = ''
credentials: dict[str, str]
is_refresh_credentials: bool = False
state: str = ''
try:
    with open(get_config_file('twitch.json')) as f:
        credentials = json.load(f)
except FileNotFoundError:
    credentials = {}


async def get_authorization_url() -> None:
    if not credentials:
        print('twitch_get_authorization_url')
        global state
        state = 'twitch-xxx'
        authorization_url = 'https://id.twitch.tv/oauth2/authorize' \
            '?response_type=code' \
            f'&client_id={CLIENT_ID}' \
            f'&redirect_uri={quote_plus("http://localhost:5173/#/main")}' \
            f'&scope={quote_plus(' '.join(SCOPES))}' \
            f'&state={state}'
        MESSAGES.append(dict(id='m', text=f'<a href="{authorization_url}">Авторизация в Twitch</a>.'))


async def get_channel_id(channel: str) -> None:
    # https://dev.twitch.tv/docs/api/reference/#get-users
    url = f'https://api.twitch.tv/helix/users?login={channel}'
    while True:
        if not credentials:
            await asyncio.sleep(TIMEOUT_30S)
            continue

        data = await make_request(url, timeout=TIMEOUT_30SF, headers=await get_headers())
        if data:
            global channel_id
            channel_id = data['data'][0]['id']
            return None
        else:
            await refresh_credentials()
            await asyncio.sleep(TIMEOUT_30S)


async def get_credentials() -> None:
    global credentials
    if not credentials:
        print('twitch_get_credentials')
        while True:
            if CONFIG['twitch']['code']:
                url = 'https://id.twitch.tv/oauth2/token'
                data = {
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'code': CONFIG['twitch']['code'],
                    'grant_type': 'authorization_code',
                    'redirect_uri': 'http://localhost:5173/#/main',
                }
                data = await make_request(url, timeout=TIMEOUT_30SF, method='POST', data=data)
                if data:
                    credentials = data
                    with get_config_file('twitch.json').open('w') as f:
                        json.dump(credentials, f)
                    return None
            await asyncio.sleep(TIMEOUT_30S)


async def get_headers() -> dict[str, str]:
    return {'Client-ID': CLIENT_ID, 'Authorization': f'Bearer {credentials['access_token']}'}


async def refresh_credentials() -> None:
    global credentials, is_refresh_credentials
    if is_refresh_credentials:
        return None
    is_refresh_credentials = True
    print('twitch_refresh_credentials')
    url = 'https://id.twitch.tv/oauth2/token'
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': credentials['refresh_token'],
    }
    credentials = {}
    data = await make_request(url, timeout=TIMEOUT_30SF, method='POST', data=data)
    if data:
        credentials = data
        with get_config_file('twitch.json').open('w') as f:
            json.dump(credentials, f)
    is_refresh_credentials = False


class Twitch(WebSocket):
    keys: list[str] = ['color', 'emotes', 'display-name', 'user-id', 'system-msg']
    text: str = CONFIG['twitch']['text']
    url: str = 'wss://irc-ws.chat.twitch.tv'

    async def add_message(self, message: D) -> None:
        message['id'] = 't'
        if message['user-id'] in FOLLOWS:
            message['timestamp'] = FOLLOWS[message['user-id']]
        message.pop('user-id')
        message['name'] = message.pop('display-name')
        await self.parse_emotes(message)
        MESSAGES.append(message)

    async def add_notify(self, message: D) -> None:
        text = self.text.format(message['system-msg'].replace(r'\s', ' '))
        MESSAGES.append(dict(id='e', text=text))

    async def clean_text(self, text: str) -> str:
        """Очищает от /me."""
        return text[8:-1] if text.startswith('\x01') else text

    async def on_message(self, data: str) -> None:
        if 'PRIVMSG' in data:
            await self.add_message(await self.parse_data(data))
        elif 'USERNOTICE' in data:
            await self.add_notify(await self.parse_data(data))
        elif data.startswith('PING'):
            await self.send_pong(data)

    async def on_open(self) -> None:
        # PASS и NICK именно в таком порядке.
        await self.w.send('PASS oauth:deaqfawg5sxy356nijwcms3r9qtkye\r\n')
        await self.w.send('NICK miranda_app\r\n')
        await self.w.send('CAP REQ :twitch.tv/tags twitch.tv/commands\r\n')
        await self.w.send(f'JOIN #{self.channel}\r\n')

    async def parse_data(self, data: str) -> D:
        parts = data.split(' ', 4)
        message = {}
        if len(parts) == 5:
            message['text'] = await self.clean_text(parts[4][1:])
        for part in parts[0].split(';'):
            k, v = part.split('=')
            if v and k in self.keys:
                message[k] = v
        return message

    async def parse_emotes(self, message: D) -> None:
        if 'emotes' not in message:
            return None
        message['replacements'] = []
        for i, emote in enumerate(message['emotes'].split('/')):
            id, indexes = emote.split(':')
            indexes = indexes.split(',', 1)[0].split('-')
            message['replacements'] += [[
                f'image{i}',
                id,
                message['text'][int(indexes[0]):int(indexes[1]) + 1],
            ]]
        message.pop('emotes')
        message['replacements'].sort(key=lambda r: r[1], reverse=True)
        for r in message['replacements']:
            message['text'] = message['text'].replace(r[2], r[0])
            del r[2]

    async def send_pong(self, data: str) -> None:
        await self.w.send(f'{data.replace("PING", "PONG")}\r\n')


class TwitchFollows(Chat):
    follows_limit: int = CONFIG['twitch'].getint('follows_limit')
    is_first_run: bool = True
    params: D = {'first': 100, 'broadcaster_id': None}
    text: str = CONFIG['twitch']['text_follower']
    # https://dev.twitch.tv/docs/api/reference/#get-channel-followers
    url: str = 'https://api.twitch.tv/helix/channels/followers'

    async def alert(self, follow: dict[str, str]) -> None:
        text = self.text.format(follow['user_name'] or follow['user_login'])
        MESSAGES.append(dict(id='e', text=text))

    async def load(self) -> int:
        data = await make_request(self.url, params=self.params, timeout=TIMEOUT_30SF, headers=await get_headers())
        if not data:
            await refresh_credentials()
            return TIMEOUT_30S
        for follow in data['data']:
            if follow['user_id'] in FOLLOWS:
                break
            FOLLOWS[follow['user_id']] = int(
                datetime.strptime(follow['followed_at'].split('T')[0], '%Y-%m-%d').timestamp(),
            )
            if not self.is_first_run:
                await self.alert(follow)
        if not self.is_first_run:
            return TIMEOUT_5M

        if len(FOLLOWS) < self.follows_limit and len(FOLLOWS) != data['total']:
            self.params['after'] = data['pagination']['cursor']
            return TIMEOUT_10S
        else:
            self.params.pop('after', None)
            self.params['first'] = 10
            self.is_first_run = False
            await self.print_error(f'запущен ({data['total']}).')
            return TIMEOUT_5M

    async def main(self) -> None:
        await self.on_start()
        if self.params['first'] > self.follows_limit:
            self.params['first'] = self.follows_limit
        try:
            while True:
                if credentials and channel_id:
                    self.params['broadcaster_id'] = channel_id
                    sleep = await self.load()
                else:
                    sleep = TIMEOUT_30S
                await asyncio.sleep(sleep)
        except asyncio.CancelledError:
            await self.on_close()
            raise


class TwitchStats(Chat):
    url: str = 'https://api.twitch.tv/helix/streams?user_login={}&first=1'

    async def alert(self, v: str) -> None:
        STATS['t'] = v

    async def load(self) -> None:
        data = await make_request(self.url, timeout=TIMEOUT_30SF, headers=await get_headers())
        if data:
            await self.alert(data['data'][0]['viewer_count'] if data['data'] else '')
        else:
            await refresh_credentials()

    async def main(self) -> None:
        await self.on_start()
        self.url = self.url.format(self.channel)
        try:
            while True:
                if credentials:
                    await self.load()
                await asyncio.sleep(TIMEOUT_30S)
        except asyncio.CancelledError:
            await self.on_close()
            raise
