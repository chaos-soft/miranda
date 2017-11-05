import socket
import time
from datetime import datetime, timedelta

import requests

from chat import Chat
from common import print_error

HEADERS = {'Accept': 'application/vnd.twitchtv.v5+json',
           'Client-ID': 'g0qvsrztagks1lbg03kwnt67pg9x8a5'}


class Twitch(Chat):

    def run(self):
        self.socket_start()

    def socket_start(self):
        try:
            s = socket.socket()
            s.connect(('irc.chat.twitch.tv', 6667))
            # Non-blocking mode.
            s.settimeout(1)

            # Именно в таком порядке.
            s.send('PASS {}\r\n'.format('oauth:q2k4wco85y82dlebbynu7f3ovke1zh'). \
                encode('utf-8'))
            s.send('NICK {}\r\n'.format('miranda_app').encode('utf-8'))

            s.send('CAP REQ :twitch.tv/tags\r\n'.encode('utf-8'))
            s.send('JOIN #{}\r\n'.format(self.channel).encode('utf-8'))

            self.print_error('{} loaded (@{}).'.format(type(self).__name__, self.channel))

            # Ориентировочное время отсылки PONG.
            pong_time = datetime.now() + timedelta(minutes=5)

            while not self.stop_event.is_set():
                try:
                    for data in s.recv(512 * 1024).decode('utf-8').split('\r\n'):
                        if not data:
                            continue
                        elif data.startswith(':twitchnotify!'):
                            self.add_notify(data)
                        elif data.startswith('PING'):
                            self.send_pong(data, s)
                            pong_time = datetime.now()
                        elif 'PRIVMSG' in data:
                            self.add_message(self.parse_data(data))
                except socket.timeout:
                    pass

                if pong_time + timedelta(minutes=5) < datetime.now():
                    break
        except (socket.error, socket.gaierror) as e:
            self.on_error(s, e)
        finally:
            self.on_close(s)

    def stop(self):
        self.join()

    def send_pong(self, data, s):
        s.send('{}\r\n'.format(data.replace('PING', 'PONG')).encode('utf-8'))

    def add_notify(self, data):
        # :twitchnotify!twitchnotify@twitchnotify.tmi.twitch.tv PRIVMSG #qwerty :xxx just subscribed!
        t = self.config['twitch']['text'].format(data.split(' ', 4)[3][1:])
        self.messages.append(dict(id='e', text=t))

    def parse_data(self, data):
        parts = data.split(' ', 4)
        result = dict(text=parts[4][1:])

        for part1 in parts[0].split(';'):
            part2 = part1.split('=')
            result[part2[0]] = part2[1]

        result['name'] = result['display-name']
        if not result['name']:
            # :chaos_soft!chaos_soft@chaos_soft.tmi.twitch.tv
            result['name'] = parts[1].split('!', 1)[0][1:]

        if result['emotes']:
            # 33:0-7/66:9-15/46:17-22/11:24-25/16:27-39/50:41-51/58127:53-59
            result['emotes'] = \
                [int(smile.split(':')[0]) for smile in result['emotes'].split('/')]

        return result

    def add_message(self, data):
        message = dict(id='t', name=data['name'], text=data['text'],
                       color=data['color'])

        self.add_role(message)

        if self.smiles and data['emotes']:
            message['replacements'] = {}

            for smile in data['emotes']:
                if smile in self.smiles:
                    url = '//static-cdn.jtvnw.net/emoticons/v1/{}/1.0'.format(smile)
                    message['replacements'][self.smiles[smile]] = url

        name_lower = data['name'].lower()
        if self.follows and name_lower in self.follows:
            message['timestamp'] = self.follows[name_lower]

        self.messages.append(message)

    def get_channel_id(self):
        url = 'https://api.twitch.tv/kraken/users?login={}'.format(self.channel)
        one_minute_countdown = 0

        while not self.stop_event.is_set():
            if one_minute_countdown > 0:
                time.sleep(5)
                one_minute_countdown -= 1
                continue

            try:
                r = requests.get(url, timeout=10, headers=HEADERS)
                r.raise_for_status()
                data = r.json()

                return data['users'][0]['_id']
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                self.print_error('{} (@{}): {}'.format(type(self).__name__, self.channel, e))

            one_minute_countdown = 12

    def load_follows(self):
        url = 'https://api.twitch.tv/kraken/channels/{}/follows?limit=100'. \
            format(self.get_channel_id())
        params = {}
        follows = {}

        while True:
            try:
                r = requests.get(url, params=params, timeout=10, headers=HEADERS)
                r.raise_for_status()
                data = r.json()

                for follow in data['follows']:
                    t = int(datetime.strptime(follow['created_at']. \
                        split('T')[0], '%Y-%m-%d').timestamp())
                    follows[follow['user']['display_name'].lower()] = t

                if '_cursor' in data and \
                   len(follows) < self.config['base'].getint('follows_limit'):
                    params['cursor'] = data['_cursor']
                else:
                    self.print_error('{} follows loaded (@{}, {}).'. \
                        format(type(self).__name__, self.channel, len(follows)))
                    return follows
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                self.print_error('{} (@{}): {}'.format(type(self).__name__, self.channel, e))
                return None

    @classmethod
    def load_smiles(cls, config, messages):
        url = 'https://api.twitch.tv/kraken/chat/emoticon_images'
        smiles = {}

        while True:
            try:
                r = requests.get(url, timeout=60, headers=HEADERS)
                r.raise_for_status()
                data = r.json()

                for smile in data['emoticons']:
                    smiles[smile['id']] = smile['code']

                print_error(messages,
                            '{} smiles loaded ({}).'.format(cls.__name__, len(smiles)))

                return smiles
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                print_error(messages, '{}: {}'.format(cls.__name__, e))
                return None
