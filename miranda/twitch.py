from datetime import datetime
import asyncio
import json

from .chat import Chat, WebSocket
from .common import make_request, MESSAGES, STATS, D
from .config import CONFIG, get_config_file

with open(get_config_file('twitch.json')) as f:
    data = json.load(f)

HEADERS: dict[str, str] = {
    'Client-ID': 'l0sytxv7tot9ynjakkx4o6ddlpn6qp',
    'Authorization': f'Bearer {data["access_token"]}',
}
TIMEOUT: float = 10.0

FOLLOWS: dict[str, int] = {}

TIMEOUT_ERROR: int = 60 * 10
TIMEOUT_NEXT: int = 5
TIMEOUT_STATS: int = 60
TIMEOUT_SUCCESS: int = 60 * 5


class Twitch(WebSocket):
    keys: list[str] = ['color', 'emotes', 'display-name', 'user-id', 'system-msg']
    text: str = CONFIG['twitch'].getlist('text')[0]
    url: str = 'wss://irc-ws.chat.twitch.tv'

    async def on_open(self) -> None:
        # PASS и NICK именно в таком порядке.
        await self.w.send('PASS oauth:deaqfawg5sxy356nijwcms3r9qtkye\r\n')
        await self.w.send('NICK miranda_app\r\n')
        await self.w.send('CAP REQ :twitch.tv/tags twitch.tv/commands\r\n')
        await self.w.send(f'JOIN #{self.channel}\r\n')

    async def on_message(self, data: str) -> None:
        if 'PRIVMSG' in data:
            await self.add_message(await self.parse_data(data))
        elif 'USERNOTICE' in data:
            await self.add_notify(await self.parse_data(data))
        elif data.startswith('PING'):
            await self.send_pong(data)

    async def send_pong(self, data: str) -> None:
        await self.w.send(f'{data.replace("PING", "PONG")}\r\n')

    async def add_notify(self, message: D) -> None:
        text = self.text.format(message['system-msg'].replace(r'\s', ' '))
        MESSAGES.append(dict(id='e', text=text))

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

    async def add_message(self, message: D) -> None:
        message['id'] = 't'
        if message['user-id'] in FOLLOWS:
            message['timestamp'] = FOLLOWS[message['user-id']]
        message.pop('user-id')
        message['name'] = message.pop('display-name')
        await self.parse_emotes(message)
        MESSAGES.append(message)

    async def clean_text(self, text: str) -> str:
        """Очищает от /me."""
        return text[8:-1] if text.startswith('\x01') else text

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


channel_id: str = ''


async def get_channel_id(channel: str) -> None:
    # https://dev.twitch.tv/docs/api/reference/#get-users
    url = f'https://api.twitch.tv/helix/users?login={channel}'
    while True:
        data = await make_request(url, timeout=TIMEOUT, headers=HEADERS)
        if data:
            global channel_id
            channel_id = data['data'][0]['id']
            break
        await asyncio.sleep(TIMEOUT_ERROR)


class TwitchFollows(Chat):
    is_first_run: bool = True
    params: D = {'first': 100, 'to_id': None}
    # https://dev.twitch.tv/docs/api/reference/#get-users-follows
    url: str = 'https://api.twitch.tv/helix/users/follows'
    text: str = CONFIG['twitch'].getlist('text')[1]

    async def main(self) -> None:
        while True:
            if channel_id:
                self.params['to_id'] = channel_id
                sleep = await self.load()
            else:
                sleep = TIMEOUT_NEXT
            await asyncio.sleep(sleep)

    async def load(self) -> int:
        data = await make_request(self.url, params=self.params, timeout=TIMEOUT, headers=HEADERS)
        if not data:
            return TIMEOUT_ERROR
        new_follows = []
        for follow in data['data']:
            if follow['from_id'] in FOLLOWS:
                break
            FOLLOWS[follow['from_id']] = int(
                datetime.strptime(follow['followed_at'].split('T')[0], '%Y-%m-%d').timestamp(),
            )
            new_follows.append(follow['from_id'])
        if not self.is_first_run:
            if new_follows:
                await self.alert(new_follows)
            return TIMEOUT_SUCCESS

        if len(FOLLOWS) < CONFIG['twitch'].getint('follows_limit') and \
           len(FOLLOWS) != data['total']:
            self.params['after'] = data['pagination']['cursor']
            return TIMEOUT_NEXT
        else:
            self.params.pop('after', None)
            self.params['first'] = 10
            self.is_first_run = False
            await self.print_error(f'запущен ({len(FOLLOWS)})')
            return TIMEOUT_SUCCESS

    async def alert(self, follows: list[str]) -> None:
        # https://dev.twitch.tv/docs/api/reference/#get-users
        url = f'https://api.twitch.tv/helix/users?id={"&id=".join(follows)}'
        data = await make_request(url, retries=2, timeout=TIMEOUT, headers=HEADERS)
        if not data:
            return None
        for follow in data['data']:
            text = self.text.format(follow['display_name'] or follow['login'])
            MESSAGES.append(dict(id='e', text=text))


class TwitchStats(Chat):
    url: str = 'https://api.twitch.tv/helix/streams?user_login={}&first=1'

    async def alert(self, v: str) -> None:
        STATS['t'] = v

    async def load(self) -> None:
        data = await make_request(self.url, timeout=TIMEOUT, headers=HEADERS)
        if data:
            await self.alert(data['data'][0]['viewer_count'] if data['data'] else '-')

    async def main(self) -> None:
        try:
            await self.on_start()
            self.url = self.url.format(self.channel)
            while True:
                await self.load()
                await asyncio.sleep(TIMEOUT_STATS)
        except asyncio.CancelledError:
            await self.on_close()
            raise
