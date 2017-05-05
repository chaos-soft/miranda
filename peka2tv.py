import json
import re

from websocket import WebSocketApp
import requests

from chat import Chat
from common import print_error


class Peka2tv(Chat):

    def run(self):
        self.re_code = re.compile(r'^(\d+).*$')
        self.text = self.config['base'].getlist('text')
        self.socket_start()

    def socket_start(self):
        self.w = WebSocketApp('wss://chat.funstream.tv',
                              on_message=self.on_message,
                              on_pong=self.on_pong,
                              on_error=self.on_error,
                              on_close=self.on_close)
        self.w.run_forever(ping_interval=30, ping_timeout=29)

    def stop(self):
        self.w.close()
        self.join()

    def on_message(self, w, data):
        code = self.re_code.search(data).group(1)
        if code == '40':
            self.join_chat(w)
        elif code == '42':
            data = json.loads(data.replace(code, '', 1))
            if data[1]['type'] == 'payment/stream':
                self.add_payment(data[1]['data'])
            elif data[1]['type'] == 'message':
                self.add_message(data[1])

    def join_chat(self, w):
        data = ['/chat/join', {'channel': 'stream/{}'.format(self.channel)}]
        w.send('421{}'.format(json.dumps(data)))
        self.print_error('{} loaded (@{}).'.format(type(self).__name__, self.channel))

    def add_message(self, data):
        name = data['from']['name']

        if data['to']:
            text = '{}, {}'.format(data['to']['name'], data['text'])
        else:
            text = data['text']

        message = dict(id='s', name=name, text=text)

        self.add_role(message)

        if self.smiles:
            m = self.re_smile.findall(text)
            if m:
                message['replacements'] = {}
            for k in m:
                if k in self.smiles:
                    message['replacements'][':{}:'.format(k)] = self.smiles[k]

        self.messages.append(message)

    def add_payment(self, data):
        if data['anonymous']:
            name = self.config['peka2tv']['text']
        else:
            name = data['user']['name']

        if data['comment']:
            t = self.text[0].format(name, data['comment'])
        else:
            t = self.text[1].format(name)

        self.messages.append(dict(id='p', text=t))

    def on_pong(self, w, _):
        w.send('2')

    @classmethod
    def load_smiles(cls, messages):
        url = 'http://funstream.tv/api/smile'
        smiles = {}

        while True:
            try:
                r = requests.get(url, timeout=60)
                r.raise_for_status()
                data = r.json()

                for smile in data:
                    smiles[smile['code']] = smile['url']

                print_error(messages,
                            '{} smiles loaded ({}).'.format(cls.__name__, len(smiles)))

                return smiles
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                print_error(messages, '{}: {}'.format(cls.__name__, e))
                return
