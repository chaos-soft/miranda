import os

from aiohttp import web
import aiohttp

from chat import Base
from common import MESSAGES, STATS
from config import BASE_DIR, CONFIG
from json_ import INSTANCEK as json

json.types_load = {'offset': int}


class Server(Base):
    names = CONFIG['base'].getlist('names')

    async def index(self, request):
        theme = request.query.get('theme') or 'base'
        with open(os.path.join(BASE_DIR, f'templates/{theme}.html')) as f:
            text = f.read(). \
                replace('{{ names }}', "', '".join(self.names)). \
                replace('{{ tts_api_key }}', CONFIG['base'].get('tts_api_key', ''))
        return web.Response(text=text, content_type='text/html')

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

    async def messages(self, request):
        w = web.WebSocketResponse()
        await w.prepare(request)
        async for message in w:
            if message.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(message.data)
                offset = data.get('offset', 0)
                total = len(MESSAGES)
                if offset > total:
                    offset = 0
                await w.send_json({
                    'messages': MESSAGES.data[offset:],
                    'stats': STATS,
                    'total': total,
                }, dumps=json.dumps)
        return w
