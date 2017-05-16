import os
import httplib2
import time

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
import cherrypy
from chat import Chat
from common import AUTHORIZATION_ANCHOR


class YouTube(Chat):
    api = None

    def __init__(self, *args):
        self.base_dir = args[-1]
        self.storage = Storage(os.path.join(self.base_dir, 'youtube_oauth2.json'))
        credentials = self.storage.get()

        if not credentials or credentials.invalid:
            self.flow = flow_from_clientsecrets(
                os.path.join(self.base_dir, 'client_secrets.json'),
                scope='https://www.googleapis.com/auth/youtube.readonly',
                redirect_uri='http://localhost:55555/youtube/')
            auth_uri = self.flow.step1_get_authorize_url()

            t = AUTHORIZATION_ANCHOR.format(auth_uri, type(self).__name__)
            args[2].append(dict(id='m', text=t))
        else:
            self.get_api(credentials)

        super().__init__(*args)

    def get_api(self, credentials):
        self.api = build('youtube', 'v3',
                         http=credentials.authorize(httplib2.Http()))

    def run(self):
        if not self.api:
            cherrypy.tree.mount(self, '/youtube')
        else:
            self.socket_start()

    def get_chat_id(self):
        one_minute_countdown = 0
        is_error = False

        while not self.stop_event.is_set():
            if one_minute_countdown > 0:
                time.sleep(5)
                one_minute_countdown -= 1
                continue

            r = self.api.liveBroadcasts().list(part='snippet',
                                               broadcastStatus='active',
                                               broadcastType='all').execute()
            chat_id = r['items'][0]['snippet']['liveChatId'] if r['items'] else None

            if not chat_id:
                if not is_error:
                    is_error = True
                    self.on_error('нет активных стримов.')

                one_minute_countdown = 12
            else:
                return chat_id

    def socket_start(self):
        try:
            chat_id = self.get_chat_id()

            if chat_id:
                request = self.api.liveChatMessages(). \
                    list(part='snippet,authorDetails', liveChatId=chat_id)

                self.on_error('запущен.')

            while not self.stop_event.is_set():
                response = request.execute()

                if response['items']:
                    for item in response['items']:
                        self.add_message(item)

                request = self.api.liveChatMessages().list_next(request, response)

                time.sleep(response['pollingIntervalMillis'] / 1000)
        except (HttpError, httplib2.ServerNotFoundError, TimeoutError) as e:
            self.on_error(e)
        finally:
            self.on_close()

    def add_message(self, data):
        message = dict(id='y', name=data['authorDetails']['displayName'],
                       text=data['snippet']['displayMessage'])
        self.add_role(message)
        self.messages.append(message)

    def stop(self):
        self.join()

    @cherrypy.expose
    def index(self, code):
        credentials = self.flow.step2_exchange(code)
        self.storage.put(credentials)
        self.get_api(credentials)
        self.config['base']['is_restart'] = 'true'

        with open(os.path.join(self.base_dir, 'templates/close.html')) as f:
            return f.read()
