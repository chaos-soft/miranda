from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import asyncio
import json

from .chat import WebSocket
from .common import T, D, MessageMiranda
from .config import CONFIG

ICONS: D = {'g': 'g.png', 't': 't.ico', 'y': 'y.ico', 'v': 'v.png'}
TASKS: T = []
TG: asyncio.TaskGroup | None = None


def get_cache_path() -> Path:
    return Path.home() / '.cache' / 'miranda'


file_path = get_cache_path() / 'smiles.json'
if not file_path.exists():
    raise FileNotFoundError(file_path)
SMILES: D = json.load(file_path.open())


async def start() -> None:
    if TASKS:
        return None
    if not TG:
        raise
    e = EwwClient('xxx')
    TASKS.append(TG.create_task(e.main()))
    get_cache_path().mkdir(mode=0o755, parents=True, exist_ok=True)


def shutdown() -> None:
    for task in TASKS:
        task.cancel()
    TASKS.clear()


class EwwClient(WebSocket):
    box: str = '(box :space-evenly false :vexpand true :spacing 4 {})'
    heartbeat: int = 5
    heartbeat_data: str = '{"offset":-2}'
    icon: str = '(image :path "{}" :image-width 16)'
    image: str = '(image :path "{}")'
    label: str = '(label :text "{}")'
    name: str = '(label :text "{}:" :show-truncated false)'
    table: Any = str.maketrans({'"': r'\"'})
    url: str = CONFIG['eww']['url']

    async def download_image(self, url: str) -> Path:
        file_path = get_cache_path() / urlparse(url).path.lstrip('/').replace('/', '__')
        if not file_path.exists():
            proc = await asyncio.create_subprocess_exec('curl', '-LJ', '-o', file_path, url)
            await proc.wait()
        return file_path

    async def eww_update(self, v: str) -> None:
        proc = await asyncio.create_subprocess_exec('eww', 'open', 'chat')
        await proc.wait()

        proc = await asyncio.create_subprocess_exec('eww', 'update', f'message={v}')
        await proc.wait()

        proc = await asyncio.create_subprocess_shell('eww update chat_selected=1')
        await proc.wait()
        await asyncio.sleep(CONFIG['eww'].getint('interval'))

        proc = await asyncio.create_subprocess_shell('eww update chat_selected=0')
        await proc.wait()
        await asyncio.sleep(0.5)

        proc = await asyncio.create_subprocess_exec('eww', 'close', 'chat')
        await proc.wait()

    async def get_image(self, url: str) -> str:
        file_path = await self.download_image(url)
        return self.image.format(file_path)

    async def on_message(self, data_str: str) -> None:
        data = json.loads(data_str)
        for message in data['messages']:
            if message['id'] == MessageMiranda.id and (not message['is_donate'] and not message['is_event']):
                continue
            elements: list[str] = list(filter(None, message['text'].translate(self.table).split(' ')))
            id = message['id']
            images = message['images']
            v = self.box.format(
                '{} {} {}'.format(
                    self.get_icon(message),
                    self.get_name(message['name']),
                    ' '.join([await self.process(text, images, id) for text in elements]),
                ),
            )
            await self.eww_update(v)
        if not data['messages']:
            await asyncio.sleep(self.heartbeat)
        self.heartbeat_data = json.dumps({'offset': data['total']})
        await self.send_heartbeat()

    async def on_open(self) -> None:
        await self.send_heartbeat()

    async def process(self, text: str, images: D, id: str) -> str:
        if id == 'g' and \
           text.startswith(':') and text.endswith(':') and \
           (smile_id := text[1:-1]) in SMILES:
            images[text] = SMILES[smile_id]

        if text in images:
            return await self.get_image(images[text])
        else:
            return self.get_label(text)

    def get_icon(self, message: D) -> str:
        if message['id'] in ICONS:
            return self.icon.format(get_cache_path() / ICONS[message['id']])
        else:
            return ''

    def get_label(self, text: str) -> str:
        return self.label.format(text)

    def get_name(self, name: str) -> str:
        return self.name.format(name)
