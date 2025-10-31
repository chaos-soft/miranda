from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import asyncio
import json

from .chat import WebSocket
from .common import T, D, EXCLUDE_IDS
from .config import CONFIG

ICONS: D = {'g': 'g.png', 't': 't.ico', 'y': 'y.ico', 'v': 'v.png'}
TASKS: T = []
TG: asyncio.TaskGroup | None = None


async def start() -> None:
    if TASKS:
        return None
    if not TG:
        raise
    e = EwwClient('xxx')
    TASKS.append(TG.create_task(e.main()))
    TASKS.append(TG.create_task(e.send_heartbeat()))
    get_cache_path().mkdir(mode=0o755, parents=True, exist_ok=True)


def get_cache_path() -> Path:
    return Path.home() / '.cache' / 'miranda'


def shutdown() -> None:
    for task in TASKS:
        task.cancel()
    TASKS.clear()


class EwwClient(WebSocket):
    box: str = '(box :space-evenly false :vexpand true :spacing 4 {})'
    heartbeat: int = 5
    heartbeat_data: str = '{"offset":0}'
    icon: str = '(image :path "{}" :image-width 16)'
    image: str = '(image :path "{}")'
    label: str = '(label :text "{}")'
    table: Any = str.maketrans({'"': r'\"'})
    url: str = CONFIG['eww']['url']

    async def download_image(self, url: str) -> Path:
        file_path = get_cache_path() / urlparse(url).path.lstrip('/').replace('/', '__')
        if not file_path.exists():
            proc = await asyncio.create_subprocess_exec('curl', '-LJ', '-o', file_path, url)
            await proc.wait()
        return file_path

    async def eww_update(self, v: str) -> None:
        proc = await asyncio.create_subprocess_exec('eww', 'update', f'message={v}')
        await proc.wait()

        proc = await asyncio.create_subprocess_shell('eww update chat_selected=1')
        await proc.wait()
        await asyncio.sleep(10)

        proc = await asyncio.create_subprocess_shell('eww update chat_selected=0')
        await proc.wait()
        await asyncio.sleep(0.5)

        # Обнулить размер на экране.
        proc = await asyncio.create_subprocess_exec('eww', 'update', 'message=')
        await proc.wait()

    async def get_image(self, url: str) -> str:
        file_path = await self.download_image(url)
        return self.image.format(file_path)

    async def on_message(self, data_str: str) -> None:
        data = json.loads(data_str)
        self.heartbeat_data = json.dumps({'offset': data['total']})
        for message in data['messages']:
            if message['id'] in EXCLUDE_IDS:
                continue
            elements: list[str] = list(filter(None, message['text'].translate(self.table).split(' ')))
            id = message['id']
            images = message.get('images', {})
            v = self.box.format(
                '{} {} {}'.format(
                    self.get_icon(message),
                    self.get_label(message['name'] + ':'),
                    ' '.join([await self.process(text, images, id) for text in elements]),
                ),
            )
            await self.eww_update(v)

    async def process(self, text: str, images: D, id: str) -> str:
        if id == 'g':
            if text.startswith(':') and text.endswith(':'):
                images[text] = f'https://goodgame.ru/images/smiles/{text[1:-1]}-big.png'

        for k, v in images.items():
            if k in text:
                return await self.get_image(v)
        else:
            return self.get_label(text)

    def get_icon(self, message: D) -> str:
        if message['id'] in ICONS:
            return self.icon.format(get_cache_path() / ICONS[message['id']])
        else:
            return ''

    def get_label(self, text: str) -> str:
        return self.label.format(text)
