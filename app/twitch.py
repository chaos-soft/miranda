from datetime import datetime
import asyncio

from chat import Chat
from common import make_request, MESSAGES, STATS
from config import CONFIG
import aiohttp

HEADERS = {
    'Client-ID': 'g0qvsrztagks1lbg03kwnt67pg9x8a5',
    'Authorization': 'Bearer 7efez7cxjfvsuaxnn7dwp7q5nnrst6',
}
TIMEOUT = aiohttp.ClientTimeout(total=10)

FOLLOWS = {}
HOSTS = []

TIMEOUT_ERROR: int = 60 * 10
TIMEOUT_NEXT: int = 5
TIMEOUT_STATS: int = 60
TIMEOUT_SUCCESS: int = 60 * 5


class Twitch(Chat):
    text = CONFIG['twitch'].getlist('text')[0]
    keys = ['color', 'emotes', 'display-name', 'user-id', 'system-msg']

    async def main(self, session):
        while True:
            await self.on_start()
            async with session.ws_connect('wss://irc-ws.chat.twitch.tv') as w:
                await self.on_open(w)
                async for message in w:
                    if message.type == aiohttp.WSMsgType.TEXT:
                        await self.on_message(message.data.rstrip(), w)
                    elif message.type == aiohttp.WSMsgType.ERROR:
                        break
                await w.close()
            await self.on_close()

    async def on_open(self, w):
        # PASS и NICK именно в таком порядке.
        await w.send_str('PASS oauth:deaqfawg5sxy356nijwcms3r9qtkye\r\n')
        await w.send_str('NICK miranda_app\r\n')
        await w.send_str('CAP REQ :twitch.tv/tags twitch.tv/commands\r\n')
        await w.send_str(f'JOIN #{self.channel}\r\n')

    async def on_message(self, data, w):
        if 'PRIVMSG' in data:
            await self.add_message(await self.parse_data(data))
        elif 'USERNOTICE' in data:
            await self.add_notify(await self.parse_data(data))
        elif data.startswith('PING'):
            await self.send_pong(data, w)

    async def send_pong(self, data, w):
        await w.send_str(f'{data.replace("PING", "PONG")}\r\n')

    async def add_notify(self, message):
        text = self.text.format(message['system-msg'].replace(r'\s', ' '))
        MESSAGES.append(dict(id='e', text=text))

    async def parse_data(self, data):
        parts = data.split(' ', 4)
        message = {}
        if len(parts) == 5:
            message['text'] = await self.clean_text(parts[4][1:])
        for part in parts[0].split(';'):
            k, v = part.split('=')
            if v and k in self.keys:
                message[k] = v
        return message

    async def add_message(self, message):
        message['id'] = 't'
        if message['user-id'] in FOLLOWS:
            message['timestamp'] = FOLLOWS[message['user-id']]
        message.pop('user-id')
        message['name'] = message.pop('display-name')
        await self.parse_emotes(message)
        MESSAGES.append(message)

    async def clean_text(self, text):
        """Очищает от /me."""
        return text[8:-1] if text.startswith('\x01') else text

    async def parse_emotes(self, message):
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


channel_id = None


async def get_channel_id(channel):
    # https://dev.twitch.tv/docs/api/reference/#get-users
    url = f'https://api.twitch.tv/helix/users?login={channel}'
    global channel_id
    while True:
        data = await make_request(url, timeout=TIMEOUT, headers=HEADERS)
        if data:
            channel_id = data['data'][0]['id']
            break
        await asyncio.sleep(TIMEOUT_ERROR)


class TwitchFollows(Chat):
    is_first_run = True
    params = {'first': 100, 'to_id': None}
    # https://dev.twitch.tv/docs/api/reference/#get-users-follows
    url = 'https://api.twitch.tv/helix/users/follows'
    text = CONFIG['twitch'].getlist('text')[1]

    async def main(self):
        while True:
            if channel_id:
                self.params['to_id'] = channel_id
                sleep = await self.load()
            else:
                sleep = TIMEOUT_NEXT
            await asyncio.sleep(sleep)

    async def load(self):
        data = await make_request(self.url, params=self.params, timeout=TIMEOUT,
                                  headers=HEADERS)
        if not data:
            return TIMEOUT_ERROR
        new_follows = []
        for follow in data['data']:
            if follow['from_id'] in FOLLOWS:
                break
            FOLLOWS[follow['from_id']] = int(
                datetime.
                strptime(follow['followed_at'].split('T')[0], '%Y-%m-%d').
                timestamp())
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

    async def alert(self, follows):
        # https://dev.twitch.tv/docs/api/reference/#get-users
        url = f'https://api.twitch.tv/helix/users?id={"&id=".join(follows)}'
        data = await make_request(url, retries=2, timeout=TIMEOUT, headers=HEADERS)
        if not data:
            return None
        for follow in data['data']:
            text = self.text.format(follow['display_name'] or follow['login'])
            MESSAGES.append(dict(id='e', text=text))


class TwitchStats(Chat):
    url = 'https://api.twitch.tv/helix/streams?user_login={}&first=1'

    async def alert(self, v: str) -> None:
        STATS['t'] = v

    async def load(self):
        data = await make_request(self.url, timeout=TIMEOUT, headers=HEADERS)
        if data:
            await self.alert(data['data'][0]['viewer_count'] if data['data'] else '-')

    async def main(self):
        await self.on_start()
        self.url = self.url.format(self.channel)
        while True:
            await self.load()
            await asyncio.sleep(TIMEOUT_STATS)
