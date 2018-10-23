import os
import httplib2

from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from apiclient.discovery import build
from apiclient.errors import HttpError
import cherrypy
from chat import Chat, Base
from common import MESSAGES, timeout_generator
from config import BASE_DIR

AUTHORIZATION_ANCHOR = '<a href="{}">Авторизация в {}</a>.'

FLOW = flow_from_clientsecrets(
    os.path.join(BASE_DIR, 'client_secrets.json'),
    scope='https://www.googleapis.com/auth/youtube.readonly',
    redirect_uri='http://localhost:55555/youtube/')
STORAGE = Storage(os.path.join(BASE_DIR, 'youtube_oauth2.json'))

TIMEOUT_CHAT_ID = 60 * 2
TIMEOUT_API = 5

api = None


def get_api():
    global api
    if api:
        return api
    credentials = STORAGE.get()
    if not credentials or credentials.invalid:
        return None
    else:
        api = build('youtube', 'v3', http=credentials.authorize(httplib2.Http()))
        return api


class YouTube(Chat):
    chat_id = None
    is_first_run = True

    def run(self):
        timeout = timeout_generator(timeout=0)
        while not self.is_stop:
            if next(timeout):
                continue
            if get_api():
                self.chat_id = self.get_chat_id()
            if not get_api():
                t = TIMEOUT_API
            elif not self.chat_id:
                t = TIMEOUT_CHAT_ID
            else:
                t = None
            if t:
                timeout = timeout_generator(timeout=t)
            else:
                break
        # Чтобы не было ошибки при закрытии программы.
        if self.chat_id:
            self.start_socket()

    def start_socket(self):
        self.on_start()
        try:
            request = get_api().liveChatMessages().list(
                part='snippet, authorDetails', liveChatId=self.chat_id)
            timeout = timeout_generator(timeout=0)
            while not self.is_stop:
                if next(timeout):
                    continue
                response = request.execute()
                if response['items']:
                    for item in response['items']:
                        self.add_message(item)
                request = get_api().liveChatMessages().list_next(request, response)
                timeout = timeout_generator(
                    timeout=(response['pollingIntervalMillis'] / 1000))
        except HttpError as e:
            self.on_error(e)
        finally:
            self.on_close()

    def get_chat_id(self):
        r = get_api().liveBroadcasts().list(part='snippet',
                                            broadcastStatus='active',
                                            broadcastType='all').execute()
        chat_id = r['items'][0]['snippet']['liveChatId'] if r['items'] else None
        if not chat_id:
            if self.is_first_run:
                self.is_first_run = False
                self.on_error('нет активных стримов.')
            return None
        else:
            return chat_id

    def add_message(self, data):
        message = dict(id='y', name=data['authorDetails']['displayName'],
                       text=data['snippet']['displayMessage'])
        MESSAGES.append(message)


class YouTubeAuthorization(Base):

    def run(self):
        if not get_api():
            url = FLOW.step1_get_authorize_url()
            text = AUTHORIZATION_ANCHOR.format(url, 'YouTube')
            MESSAGES.append(dict(id='m', text=text))
            cherrypy.tree.mount(self, '/youtube')

    @cherrypy.expose
    def index(self, code):
        credentials = FLOW.step2_exchange(code)
        STORAGE.put(credentials)
        raise cherrypy.HTTPRedirect('/')
