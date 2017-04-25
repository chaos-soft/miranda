import json
import html
import time

import requests
from websocket import WebSocketApp

from chat import Chat, print_error


class GoodGame(Chat):

    def run(self):
        self.text = list(map(str.strip, self.config['base']['text'].split(',')))
        self.socket_start()

    def socket_start(self):
        self.w = WebSocketApp('ws://chat.goodgame.ru:8081/chat/websocket',
                              on_message=self.on_message,
                              on_open=self.on_open,
                              on_error=self.on_error,
                              on_close=self.on_close)
        self.w.run_forever(ping_interval=30, ping_timeout=29)

    def stop(self):
        self.w.close()
        self.join()

    def on_open(self, w):
        data = {'type': 'join', 'data': {'channel_id': self.channel, 'hidden': False}}
        w.send(json.dumps(data))
        self.print_error('{} loaded (@{}).'.format(type(self).__name__, self.channel))

    def on_message(self, _, data):
        data = json.loads(data)
        if data['type'] == 'message':
            self.add_message(data['data'])
        elif data['type'] == 'payment':
            self.add_payment(data['data'])
        elif data['type'] == 'premium':
            self.add_premium(data['data'])

    def add_premium(self, data):
        t = self.config['goodgame']['text'].format(data['userName'])
        self.messages.append(dict(id='e', name=self.config['base']['app_name'], text=t))

    def add_message(self, data):
        name = data['user_name']

        text = self.filter(name, html.unescape(data['text']))
        if not text:
            return

        message = dict(id='g', name=name, text=text)

        if self.smiles:
            m = self.re_smile.findall(text)
            if m:
                message['replacements'] = {}
            for k in m:
                if k in self.smiles:
                    message['replacements'][':{}:'.format(k)] = self.smiles[k]

        name_lower = name.lower()
        if self.follows and name_lower in self.follows:
            message['timestamp'] = self.follows[name_lower]

        self.messages.append(message)

    def add_payment(self, data):
        if data['message']:
            t = self.text[0].format(data['userName'], data['message'])
        else:
            t = self.text[1].format(data['userName'])
        self.messages.append(dict(id='p', name=self.config['base']['app_name'], text=t))

    def load_follows(self):
        url = 'http://api2.goodgame.ru/channel/{}/subscribers?access_token={}'. \
            format(self.channel, self.config['goodgame']['token'])
        params = {}
        follows = {}

        while True:
            try:
                r = requests.get(url, params=params, timeout=10)
                r.raise_for_status()
                data = r.json()

                for s in data['_embedded']['subscribers']:
                    if not s['id']:
                        continue
                    follows[s['username'].lower()] = int(s['created_at'])

                if data['page'] < data['page_count'] and \
                   len(follows) < int(self.config['base']['follows_limit']):
                    params['page'] = data['page'] + 1
                else:
                    self.print_error('{} follows loaded (@{}, {}).'. \
                        format(type(self).__name__, self.channel, len(follows)))
                    return follows
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                self.print_error('{} (@{}): {}'.format(type(self).__name__, self.channel, e))
                if '401' in str(e):
                    t = '<a href="http://api2.goodgame.ru/oauth/authorize?response_type=token&' \
                        'client_id={}&scope=channel.subscribers&state=xxx" target="_blank">Token</a>.'. \
                        format(self.config['goodgame']['client_id'])
                    self.messages.append(
                        dict(id='m', name=self.config['base']['app_name'], text=t))
                    return
                elif '403' in str(e):
                    return
                time.sleep(60)

    @classmethod
    def load_smiles(cls, messages):
        url = 'http://api2.goodgame.ru/smiles'
        params = {}
        smiles = {}

        while True:
            try:
                r = requests.get(url, params=params, timeout=10)
                r.raise_for_status()
                data = r.json()

                for s in data['_embedded']['smiles']:
                    url_ = s['urls']['gif'] if s['urls']['gif'] else s['urls']['big']
                    smiles[s['key']] = url_

                if data['page'] < data['page_count']:
                    params['page'] = data['page'] + 1
                else:
                    print_error(messages,
                                '{} smiles loaded ({}).'.format(cls.__name__, len(smiles)))
                    return smiles
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                print_error(messages, '{}: {}'.format(cls.__name__, e))
                time.sleep(60)
