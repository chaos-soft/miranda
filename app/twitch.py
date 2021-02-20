from datetime import datetime
import asyncio

from chat import Chat
from common import MESSAGES, make_request
from config import CONFIG
import aiohttp

HEADERS = {
    'Client-ID': 'l0sytxv7tot9ynjakkx4o6ddlpn6qp',
    'Authorization': 'Bearer upk86jkjcnqxem2ds5kz1ua4huavet',
}
TIMEOUT = aiohttp.ClientTimeout(total=10)

FOLLOWS = {}
HOSTS = []

TIMEOUT_SUCCESS = 60 * 5
TIMEOUT_ERROR = 60 * 10
TIMEOUT_NEXT = 5


class Twitch(Chat):
    text = CONFIG['twitch'].getlist('text')[0]

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
        if 'USERNOTICE' in data:
            await self.add_notify(await self.parse_data(data))
        elif data.startswith('PING'):
            await self.send_pong(data, w)
        elif 'PRIVMSG' in data:
            await self.add_message(await self.parse_data(data))

    async def send_pong(self, data, w):
        await w.send_str(f'{data.replace("PING", "PONG")}\r\n')

    async def add_notify(self, data):
        text = self.text.format(data['system-msg'].replace(r'\s', ' '))
        MESSAGES.append(dict(id='e', text=text))

    async def parse_data(self, data):
        parts = data.split(' ', 4)
        result = dict(text=(parts[4][1:] if len(parts) == 5 else None))
        # Сохраняет все ключи и значения.
        for part in parts[0].split(';'):
            k, v = part.split('=')
            result[k] = v
        result['name'] = result['display-name']
        if not result['name']:
            # :chaos_soft!chaos_soft@chaos_soft.tmi.twitch.tv
            result['name'] = parts[1].split('!', 1)[0][1:]
        return result

    async def add_message(self, data):
        message = dict(id='t', name=data['name'],
                       text=await self.clean_text(data['text']),
                       color=data['color'], emotes=data['emotes'])
        if data['user-id'] in FOLLOWS:
            message['timestamp'] = FOLLOWS[data['user-id']]
        MESSAGES.append(message)

    async def clean_text(self, text):
        """Очищает от /me."""
        return text[8:-1] if text.startswith('\x01') else text


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
    text = CONFIG['twitch'].getlist('text')[2]

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
            await self.print_error(f'{{}} запущен ({len(FOLLOWS)}).')
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


class TwitchHosts(Chat):
    is_first_run = True
    channel_id = None
    # Недокументированное.
    url = 'https://tmi.twitch.tv/hosts?include_logins=1&target={}'
    text = CONFIG['twitch'].getlist('text')[1]

    async def main(self):
        while True:
            if channel_id:
                self.url = self.url.format(channel_id)
                sleep = await self.load()
            else:
                sleep = TIMEOUT_NEXT
            await asyncio.sleep(sleep)

    async def load(self):
        data = await make_request(self.url, timeout=TIMEOUT)
        if not data:
            return TIMEOUT_ERROR
        new_hosts = []
        for host in data['hosts']:
            if host['host_id'] in HOSTS:
                break
            HOSTS.append(host['host_id'])
            new_hosts.append(host['host_display_name'] or host['host_login'])
        if new_hosts and not self.is_first_run:
            await self.alert(new_hosts)
        if self.is_first_run:
            self.is_first_run = False
            await self.print_error(f'{{}} запущен ({len(HOSTS)}).')
        return TIMEOUT_SUCCESS

    async def alert(self, hosts):
        for host in hosts:
            text = self.text.format(host)
            MESSAGES.append(dict(id='e', text=text))
