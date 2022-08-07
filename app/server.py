import os

from aiohttp import web
import aiohttp

from chat import Base
from common import MESSAGES, STATS
from config import CONFIG
from json_ import INSTANCEK as json

json.types_load = {'offset': int}


class Server(Base):
    names = CONFIG['base'].getlist('names')
    tts_api_key = CONFIG['base'].get('tts_api_key')

    async def main(self):
        await self.on_start()
        app = web.Application()
        app.add_routes([
            web.get('/', self.messages),
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
                    'names': self.names,
                    'stats': STATS,
                    'total': total,
                    'tts_api_key': self.tts_api_key,
                }, dumps=json.dumps)
        return w
