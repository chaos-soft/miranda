import os

from aiohttp import web

from common import MESSAGES
from config import BASE_DIR, CONFIG
from chat import Base


class Server(Base):
    names = CONFIG['base'].getlist('names')

    async def main(self):
        await self.on_start()
        app = web.Application()
        app.add_routes([
            web.get('/', self.index),
            web.get('/messages', self.messages),
            web.static('/store', os.path.join(BASE_DIR, 'store')),
        ])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 55555)
        await site.start()

    async def index(self, request):
        theme = request.query.get('theme') or 'base'
        with open(os.path.join(BASE_DIR, f'templates/{theme}.html')) as f:
            text = f.read(). \
                replace('{{ names }}', "', '".join(self.names)). \
                replace('{{ tts_api_key }}', CONFIG['base'].get('tts_api_key', ''))
        return web.Response(text=text, content_type='text/html')

    async def messages(self, request):
        total = len(MESSAGES)
        offset = int(request.query['offset'])
        if offset > total:
            offset = 0
        return web.json_response({'messages': MESSAGES.data[offset:], 'total': total})
