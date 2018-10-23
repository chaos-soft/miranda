import os

import cherrypy

from common import MESSAGES
from config import BASE_DIR, CONFIG
from chat import Base


class Server(Base):
    names = CONFIG['base'].getlist('names')

    def run(self):
        self.on_start()
        config = {
            '/store': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': os.path.join(BASE_DIR, 'store'),
            },
        }
        cherrypy.config.update({
            'log.screen': False,
            'log.access_file': '',
            'log.error_file': '',
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 55555,
            'engine.autoreload.on': False,
        })
        cherrypy.quickstart(self, '/', config)

    def stop(self):
        cherrypy.engine.exit()
        self.on_close()
        super().stop()

    @cherrypy.expose
    def index(self, theme='base'):
        with open(os.path.join(BASE_DIR, 'templates/{}.html'.format(theme))) as f:
            return (
                f.read().
                replace('{{ names }}', ', '.join('"{}"'.format(n) for n in self.names)).
                replace('{{ tts_api_key }}', CONFIG['base'].get('tts_api_key', '')))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def messages(self, offset):
        total = len(MESSAGES)
        offset = int(offset)
        if offset > total:
            offset = 0
        return {'messages': MESSAGES[offset:], 'total': total}
