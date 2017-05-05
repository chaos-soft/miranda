import socket
import time
import threading
from datetime import datetime

import requests

from chat import Chat
from common import print_error


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
            s.send('PASS {}\r\n'.format(self.config['twitch']['pass']).encode('utf-8'))
            s.send('NICK {}\r\n'.format(self.config['twitch']['nick']).encode('utf-8'))

            s.send('CAP REQ :twitch.tv/tags\r\n'.encode('utf-8'))
            s.send('JOIN #{}\r\n'.format(self.channel).encode('utf-8'))

            self.print_error('{} loaded (@{}).'.format(type(self).__name__, self.channel))

            while not self.stop_event.is_set():
                try:
                    for data in s.recv(524288).decode('utf-8').split('\r\n'):
                        if not data:
                            continue
                        elif data.startswith(':twitchnotify!'):
                            self.add_notify(data)
                        elif data.startswith('PING'):
                            self.send_pong(data, s)
                        elif 'PRIVMSG' in data:
                            self.add_message(data)
                except socket.timeout:
                    pass
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

    def add_message(self, data):
        parts = data.split(' ', 4)
        data = parts[0].split(';')

        name = data[2].split('=')[1]
        if not name:
            name = parts[1].split('!', 1)[0][1:]

        message = dict(id='t', name=name, text=parts[4][1:],
                       color=data[1].split('=')[1])

        self.add_role(message)

        if self.smiles:
            try:
                smiles = list(filter(bool, data[3].split('=')[1].split('/')))
                if smiles:
                    message['replacements'] = {}
                for smile in smiles:
                    k = int(smile.split(':')[0])
                    if k in self.smiles:
                        url = '//static-cdn.jtvnw.net/emoticons/v1/{}/1.0'.format(k)
                        message['replacements'][self.smiles[k]] = url
            except IndexError:
                pass

        name_lower = name.lower()
        if self.follows and name_lower in self.follows:
            message['timestamp'] = self.follows[name_lower]

        self.messages.append(message)

    def get_channel_id(self):
        url = 'https://api.twitch.tv/kraken/users?login={}'.format(self.channel)
        headers = {'Accept': 'application/vnd.twitchtv.v5+json',
                   'Client-ID': self.config['twitch']['client_id']}

        while True:
            try:
                r = requests.get(url, timeout=10, headers=headers)
                r.raise_for_status()
                data = r.json()

                return data['users'][0]['_id']
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                self.print_error('{} (@{}): {}'.format(type(self).__name__, self.channel, e))
                time.sleep(60)

    def load_follows(self):
        url = 'https://api.twitch.tv/kraken/channels/{}/follows?limit=100'. \
            format(self.get_channel_id())
        headers = {'Accept': 'application/vnd.twitchtv.v5+json',
                   'Client-ID': self.config['twitch']['client_id']}
        params = {}
        follows = {}

        while True:
            try:
                r = requests.get(url, params=params, timeout=10, headers=headers)
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
                return

    @classmethod
    def load_smiles(cls, config, messages):
        url = 'https://api.twitch.tv/kraken/chat/emoticon_images'
        smiles = {}
        headers = {'Accept': 'application/vnd.twitchtv.v5+json',
                   'Client-ID': config['twitch']['client_id']}

        while True:
            try:
                r = requests.get(url, timeout=60, headers=headers)
                r.raise_for_status()
                data = r.json()

                for smile in data['emoticons']:
                    smiles[smile['id']] = smile['code']

                print_error(messages,
                            '{} smiles loaded ({}).'.format(cls.__name__, len(smiles)))

                return smiles
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                print_error(messages, '{}: {}'.format(cls.__name__, e))
                return
