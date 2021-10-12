from typing import Optional, Union
import json

import cherrypy

from common import Base, MESSAGES, STATS


class Server(Base):
    def add_headers(self) -> None:
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'x-requested-with'
        cherrypy.response.headers['Access-Control-Allow-Method'] = 'GET'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = 'null'

    def messages(self, offset: Union[int, str]) -> Optional[str]:
        self.add_headers()
        if cherrypy.request.method == 'OPTIONS':
            cherrypy.response.status = '204 No Content'
            return None
        offset = int(offset)
        total = len(MESSAGES)
        if offset > total:
            offset = 0
        return json.dumps({'messages': MESSAGES[offset:], 'total': total},
                          ensure_ascii=False)

    def run(self) -> None:
        self.on_start()
        cherrypy.config.update({
            'engine.autoreload.on': False,
            'log.access_file': '',
            'log.error_file': '',
            'log.screen': False,
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 55555,
        })
        cherrypy.quickstart(self)
        self.on_stop()

    def stats(self) -> Optional[str]:
        self.add_headers()
        if cherrypy.request.method == 'OPTIONS':
            cherrypy.response.status = '204 No Content'
            return None
        return json.dumps({'stats': STATS}, ensure_ascii=False)

    def stop(self) -> None:
        cherrypy.engine.exit()
        super().stop()

    messages.exposed = True
    stats.exposed = True
