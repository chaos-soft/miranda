import socket
from datetime import datetime, timedelta

from chat import Chat
from common import MESSAGES, make_request, timeout_generator
from config import CONFIG

HEADERS = {'Client-ID': 'g0qvsrztagks1lbg03kwnt67pg9x8a5'}
TIMEOUT = 10

FOLLOWS = {}
HOSTS = []

TIMEOUT_SUCCESS = 60 * 5
TIMEOUT_ERROR = 60 * 10
TIMEOUT_NEXT = 5


class Twitch(Chat):
    text = CONFIG['twitch'].getlist('text')[0]

    def run(self):
        self.start_socket()

    def start_socket(self):
        self.on_start()
        s = self.get_socket()
        # Ориентировочное время отсылки PONG.
        pong_time = datetime.now() + timedelta(minutes=5)
        # Массив для сборки сообщения, так как оно может приходить
        # разбитым на несколько чатей. Ориентир последней — '\r\n'
        # в конце строки.
        data_list = []
        while not self.is_stop:
            try:
                data_list.append(s.recv(512 * 1024))
                if not data_list[-1].endswith(b'\r\n'):
                    self.on_error('not endswith')
                    continue
                for data in b''.join(data_list).decode('utf-8').split('\r\n'):
                    if 'USERNOTICE' in data:
                        self.add_notify(self.parse_data(data))
                    elif data.startswith('PING'):
                        self.send_pong(data, s)
                        pong_time = datetime.now()
                    elif 'PRIVMSG' in data:
                        self.add_message(self.parse_data(data))
                data_list = []
            except socket.timeout:
                pass
            if pong_time + timedelta(minutes=5) < datetime.now():
                self.on_error('pong_time')
                break
        self.on_close(s)

    def get_socket(self):
        s = socket.socket()
        s.connect(('irc.chat.twitch.tv', 6667))
        # Non-blocking mode.
        s.settimeout(1)
        # PASS и NICK именно в таком порядке.
        s.send('PASS {}\r\n'.format('oauth:q2k4wco85y82dlebbynu7f3ovke1zh').encode('utf-8'))
        s.send('NICK {}\r\n'.format('miranda_app').encode('utf-8'))
        s.send('CAP REQ :twitch.tv/tags twitch.tv/commands\r\n'.encode('utf-8'))
        s.send('JOIN #{}\r\n'.format(self.channel).encode('utf-8'))
        return s

    def send_pong(self, data, s):
        s.send('{}\r\n'.format(data.replace('PING', 'PONG')).encode('utf-8'))

    def add_notify(self, data):
        text = self.text.format(data['system-msg'].replace(r'\s', ' '))
        MESSAGES.append(dict(id='e', text=text))

    def parse_data(self, data):
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

    def add_message(self, data):
        message = dict(id='t', name=data['name'],
                       text=self.clean_text(data['text']),
                       color=data['color'], emotes=data['emotes'])
        if data['user-id'] in FOLLOWS:
            message['timestamp'] = FOLLOWS[data['user-id']]
        MESSAGES.append(message)

    def clean_text(self, text):
        """Очищает от /me."""
        return text[8:-1] if text.startswith('\x01') else text


def get_channel_id(channel):
    # https://dev.twitch.tv/docs/api/reference/#get-users
    url = 'https://api.twitch.tv/helix/users?login={}'.format(channel)
    data = make_request(url, timeout=TIMEOUT, headers=HEADERS)
    return data['data'][0]['id'] if data else None


class TwitchFollows(Chat):
    is_first_run = True
    params = {'first': 100, 'to_id': None}
    # https://dev.twitch.tv/docs/api/reference/#get-users-follows
    url = 'https://api.twitch.tv/helix/users/follows'
    text = CONFIG['twitch'].getlist('text')[2]

    def run(self):
        timeout = timeout_generator(timeout=0)
        while not self.is_stop:
            if next(timeout):
                continue
            if not self.params['to_id']:
                self.params['to_id'] = get_channel_id(self.channel)
            t = self.load() if self.params['to_id'] else TIMEOUT_ERROR
            timeout = timeout_generator(timeout=t)

    def stop(self):
        self.on_close()
        super().stop()

    def load(self):
        data = make_request(self.url, params=self.params, timeout=TIMEOUT,
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
                self.alert(new_follows)
            return TIMEOUT_SUCCESS

        if len(FOLLOWS) < CONFIG['twitch'].getint('follows_limit') and \
           len(FOLLOWS) != data['total']:
            self.params['after'] = data['pagination']['cursor']
            return TIMEOUT_NEXT
        else:
            self.params.pop('after', None)
            self.params['first'] = 10
            self.is_first_run = False
            self.print_error('{} запущен ({}).', len(FOLLOWS))
            return TIMEOUT_SUCCESS

    def alert(self, follows):
        # https://dev.twitch.tv/docs/api/reference/#get-users
        url = 'https://api.twitch.tv/helix/users?id={}'.format('&id='.join(follows))
        data = make_request(url, 2, timeout=TIMEOUT, headers=HEADERS)
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

    def run(self):
        timeout = timeout_generator(timeout=0)
        while not self.is_stop:
            if next(timeout):
                continue
            if not self.channel_id:
                self.channel_id = get_channel_id(self.channel)
                if self.channel_id:
                    self.url = self.url.format(self.channel_id)
            t = self.load() if self.channel_id else TIMEOUT_ERROR
            timeout = timeout_generator(timeout=t)

    def stop(self):
        self.on_close()
        super().stop()

    def load(self):
        data = make_request(self.url, timeout=TIMEOUT, headers=HEADERS)
        if not data:
            return TIMEOUT_ERROR
        new_hosts = []
        for host in data['hosts']:
            if host['host_id'] in HOSTS:
                break
            HOSTS.append(host['host_id'])
            new_hosts.append(host['host_display_name'] or host['host_login'])
        if new_hosts and not self.is_first_run:
            self.alert(new_hosts)
        if self.is_first_run:
            self.is_first_run = False
            self.print_error('{} запущен ({}).', len(HOSTS))
        return TIMEOUT_SUCCESS

    def alert(self, hosts):
        for host in hosts:
            text = self.text.format(host)
            MESSAGES.append(dict(id='e', text=text))
