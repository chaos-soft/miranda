import json
import html

from websocket import WebSocketApp

from chat import Chat
from common import MESSAGES
from config import CONFIG


class GoodGame(Chat):
    text = CONFIG['base'].getlist('text')

    def run(self):
        self.start_socket()

    def stop(self):
        self.w.close()
        super().stop()

    def start_socket(self):
        self.on_start()
        self.w = WebSocketApp('wss://chat.goodgame.ru/chat/websocket',
                              on_message=self.on_message,
                              on_open=self.on_open,
                              on_error=self.on_error,
                              on_close=self.on_close)
        self.w.run_forever()

    def on_open(self, w):
        data = {
            'type': 'join',
            'data': {
                'channel_id': self.channel,
                'hidden': False,
            },
        }
        w.send(json.dumps(data))

    def on_message(self, w, data):
        data = json.loads(data)
        if data['type'] == 'message':
            self.add_message(data['data'])
        elif data['type'] == 'payment':
            self.add_payment(data['data'])
        elif data['type'] == 'premium':
            self.add_premium(data['data'])

    def add_premium(self, data):
        text = CONFIG['goodgame']['text'].format(data['userName'])
        MESSAGES.append(dict(id='e', text=text))

    def add_message(self, data):
        message = dict(id='g', name=data['user_name'],
                       text=html.unescape(data['text']),
                       premiums=data['premiums'])
        MESSAGES.append(message)

    def add_payment(self, data):
        if data['message']:
            text = self.text[0].format(data['userName'], data['message'])
        else:
            text = self.text[1].format(data['userName'])
        MESSAGES.append(dict(id='p', text=text))
