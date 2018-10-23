import json
import re
import ssl

from websocket import WebSocketApp

from chat import Chat
from common import MESSAGES


class Peka2tv(Chat):
    re_code = re.compile(r'^\d+')

    def run(self):
        self.start_socket()

    def stop(self):
        self.w.close()
        super().stop()

    def start_socket(self):
        self.on_start()
        self.w = WebSocketApp('wss://chat.peka2.tv',
                              on_message=self.on_message,
                              on_pong=self.on_pong,
                              on_error=self.on_error,
                              on_close=self.on_close)
        self.w.run_forever(ping_interval=30, ping_timeout=29,
                           sslopt={'cert_reqs': ssl.CERT_NONE})

    def on_message(self, w, data):
        code = self.re_code.search(data).group(0)
        if code == '40':
            self.join_chat(w)
        elif code == '42':
            data = json.loads(data.replace(code, '', 1))
            if data[1]['type'] == 'message':
                self.add_message(data[1])

    def join_chat(self, w):
        data = ['/chat/join', {'channel': 'stream/{}'.format(self.channel)}]
        w.send('421{}'.format(json.dumps(data)))

    def add_message(self, data):
        if data['to']:
            text = '{}, {}'.format(data['to']['name'], data['text'])
        else:
            text = data['text']
        message = dict(id='s', name=data['from']['name'], text=text)
        MESSAGES.append(message)

    def on_pong(self, w, data):
        w.send('2')
