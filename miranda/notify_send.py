from pathlib import Path
from urllib.parse import urlparse
import asyncio
import json

from .chat import WebSocket
from .common import T, D, MessageMiranda
from .config import CONFIG

ICONS: D = {"g": "g.png", "t": "t.ico", "y": "y.ico", "v": "v.png"}
NAMES: D = {"g": "gg", "t": "tw", "y": "yt", "v": "vk"}
TASKS: T = []
TG: asyncio.TaskGroup | None = None


def get_cache_path() -> Path:
    return Path.home() / ".cache" / "miranda"


file_path = get_cache_path() / "smiles.json"
if not file_path.exists():
    raise FileNotFoundError(file_path)
SMILES: D = json.load(file_path.open())


async def start() -> None:
    if TASKS:
        return None
    if not TG:
        raise
    n = NotifySend("xxx")
    TASKS.append(TG.create_task(n.main()))
    get_cache_path().mkdir(mode=0o755, parents=True, exist_ok=True)


def shutdown() -> None:
    for task in TASKS:
        task.cancel()
    TASKS.clear()


class NotifySend(WebSocket):
    heartbeat: int = 5
    heartbeat_data: str = '{"offset":-2}'
    url: str = CONFIG["notify_send"]["url"]

    async def download_image(self, url: str) -> Path:
        file_path = get_cache_path() / urlparse(url).path.lstrip("/").replace("/", "__")
        if not file_path.exists():
            proc = await asyncio.create_subprocess_exec(
                "curl", "-LJ", "-o", file_path, url
            )
            await proc.wait()
        return file_path

    async def notify_send(self, icon: str, message: D) -> None:
        if message["id"] in NAMES:
            name = "[{}] {}".format(NAMES[message["id"]], message["name"])
        else:
            name = message["name"]
        proc = await asyncio.create_subprocess_exec(
            "notify-send",
            "-i",
            icon,
            name,
            message["text"].replace("-", r"\-"),
        )
        await proc.wait()

    async def on_message(self, data_str: str) -> None:
        data = json.loads(data_str)
        for message in data["messages"]:
            if message["id"] == MessageMiranda.id and (
                not message["is_donate"] and not message["is_event"]
            ):
                continue
            elements: list[str] = list(filter(None, message["text"].split(" ")))
            icon = ""
            id = message["id"]
            images = message["images"]
            for text in elements:
                icon = await self.process(text, images, id)
                if icon:
                    break
            if not icon:
                icon = self.get_icon(message)
            await self.notify_send(icon, message)
        await asyncio.sleep(self.heartbeat)
        self.heartbeat_data = json.dumps({"offset": data["total"]})
        await self.send_heartbeat()

    async def on_open(self) -> None:
        await self.send_heartbeat()

    async def process(self, text: str, images: D, id: str) -> str:
        if (
            id == "g"
            and text.startswith(":")
            and text.endswith(":")
            and (smile_id := text[1:-1]) in SMILES
        ):
            images[text] = SMILES[smile_id]

        if text in images:
            return str(await self.download_image(images[text]))
        else:
            return ""

    def get_icon(self, message: D) -> str:
        if message["id"] in ICONS:
            return str(get_cache_path() / ICONS[message["id"]])
        else:
            return ""
