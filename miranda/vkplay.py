from base64 import standard_b64encode
from urllib.parse import quote_plus
import asyncio
import json

from .chat import Chat, OAuth, WebSocket
from .common import (
    D,
    MESSAGES,
    MessageABC,
    MessageMiranda,
    STATS,
    create_task,
    logger,
    make_request,
)
from .config import CONFIG

CLIENT_ID: str = "534nwhjhsn894my7"
CLIENT_SECRET: str = "DjTki7eQbDA7hfSLH9znrhmdanq6lRFXbsMIHF5k2nkw5OobkVHy4eQITZmYYqcG"
TIMEOUT_1M: int = 1 * 60
TIMEOUT_30S: int = 30


async def start() -> None:
    channel = CONFIG["vkplay"].get("channel", "")
    oauth = OAuthVK(channel)
    create_task(oauth.main())
    await oauth.credentials_event.wait()
    stats = VKStats(channel, oauth)
    create_task(stats.main())
    await stats.channel_id_event.wait()
    create_task(VK(channel, oauth, stats).main())


class Message(MessageABC):
    id = "v"


class OAuthVK(OAuth):
    authorization: str = standard_b64encode(
        ":".join([CLIENT_ID, CLIENT_SECRET]).encode("utf-8")
    ).decode("utf-8")
    authorization_url: str = "https://auth.live.vkvideo.ru/app/oauth2/authorize"
    file_name: str = "vkplay.json"
    headers: dict[str, str] = {
        "Authorization": f"Basic {authorization}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    lock: asyncio.Lock
    state: str = "vkplay-xxx"
    token_url: str = "https://api.live.vkvideo.ru/oauth/server/token"

    def __init__(self, channel: str) -> None:
        super().__init__(channel)
        self.lock = asyncio.Lock()

    async def get_authorization_url(self) -> None:
        if self.credentials_event.is_set() or CONFIG["vkplay"]["code"]:
            return None
        await self.on_start("get_authorization_url()")
        url = "".join(
            [
                self.authorization_url,
                "?response_type=code",
                "&client_id=",
                CLIENT_ID,
                "&redirect_uri=",
                quote_plus(self.redirect_uri),
                "&state=",
                self.state,
            ]
        )
        text = f'<a href="{url}">Авторизация в VK</a>.'
        MESSAGES.append(MessageMiranda(text=text))

    async def get_credentials(self) -> None:
        if self.credentials_event.is_set() or not CONFIG["vkplay"]["code"]:
            return None
        await self.on_start("get_credentials()")
        while True:
            data = {
                "code": CONFIG["vkplay"]["code"],
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            }
            d = await make_request(
                self.token_url,
                method="POST",
                data=data,
                headers=self.headers,
            )
            if d:
                self.credentials = d
                self.credentials_event.set()
                self.dump_credentials()
                return None
            else:
                await asyncio.sleep(TIMEOUT_30S)

    async def main(self) -> None:
        await self.get_authorization_url()
        await self.get_credentials()

    async def refresh_credentials(self) -> None:
        if self.lock.locked():
            return None
        async with self.lock:
            await self.on_start("refresh_credentials()")
            data = {
                "grant_type": "refresh_token",
                "redirect_uri": self.redirect_uri,
                "refresh_token": self.credentials["refresh_token"],
            }
            data = await make_request(
                self.token_url,
                method="POST",
                data=data,
                headers=self.headers,
            )
            if data:
                self.credentials = data
                self.credentials_event.set()
                self.dump_credentials()

    def get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.credentials['access_token']}"}


class VKStats(Chat):
    channel_id: int = 0
    channel_id_event: asyncio.Event
    oauth: OAuthVK
    url: str = "https://apidev.live.vkvideo.ru/v1/channel?channel_url={}"

    def __init__(self, channel: str, oauth: OAuthVK) -> None:
        super().__init__(channel)
        self.channel_id_event = asyncio.Event()
        self.oauth = oauth
        self.url = self.url.format(channel)

    async def load(self) -> None:
        data = await make_request(
            self.url, headers=self.oauth.get_headers(), is_status_code=True
        )
        if isinstance(data, dict):
            self.channel_id = data["data"]["channel"]["id"]
            self.channel_id_event.set()
            self.alert(data["data"]["stream"]) if data["data"]["stream"] else None
        elif isinstance(data, int):
            if data == 401:
                self.add_error()
                self.oauth.delete_credentials_file()
                raise asyncio.CancelledError()
            else:
                await self.oauth.refresh_credentials()

    async def main(self) -> None:
        await self.on_start()
        self.add_info()
        try:
            while True:
                await self.load()
                await asyncio.sleep(TIMEOUT_1M)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    def add_error(self) -> None:
        text = "Необходимо авторизоваться заново в VK."
        MESSAGES.append(MessageMiranda(text=text))

    def add_info(self) -> None:
        text = "Статистика с VK: views, reactions, viewers."
        MESSAGES.append(MessageMiranda(text=text))

    def alert(self, data: D) -> None:
        views: int = data["counters"]["views"]
        reactions: int = sum(map(lambda r: r["count"], data["reactions"]))
        viewers: int = data["counters"]["viewers"]
        STATS["v"] = f"{views} {reactions} {viewers}"


class VK(WebSocket):
    oauth: OAuthVK
    stats: VKStats
    url: str = (
        "wss://pubsub-dev.live.vkvideo.ru/connection/websocket"
        + "?format=json&cf_protocol_version=v2"
    )

    def __init__(self, channel: str, oauth: OAuthVK, stats: VKStats) -> None:
        super().__init__(channel)
        self.oauth = oauth
        self.stats = stats

    async def get_chat_token(self) -> str:
        url = "https://apidev.live.vkvideo.ru/v1/websocket/token"
        while True:
            data = await make_request(url, headers=self.oauth.get_headers())
            if data:
                chat_token = data["data"]["token"]
                return chat_token
            else:
                await self.oauth.refresh_credentials()

    async def on_message(self, data_str: str) -> None:
        assert self.w is not None

        if data_str == "{}":
            await self.w.send(data_str)
            return None

        for v in data_str.split("\n"):
            data = json.loads(v)
            if "connect" in data:
                data = '{"subscribe":{"channel":"channel-chat:{}"},"id":2}'
                await self.w.send(data.replace("{}", str(self.stats.channel_id)))
            elif "push" in data:
                if data["push"]["pub"]["data"]["type"] == "delete_message":
                    pass
                elif data["push"]["pub"]["data"]["type"] == "message":
                    self.add_message(data["push"]["pub"]["data"]["data"])
                else:
                    logger.info(data)
            else:
                logger.info(data)

    async def on_open(self) -> None:
        assert self.w is not None
        chat_token = await self.get_chat_token()
        data = {
            "connect": {
                "token": chat_token,
                "name": "js",
            },
            "id": 1,
        }
        await self.w.send(json.dumps(data))

    def add_message(self, message: D) -> None:
        images: D = {}
        name = message["user"]["displayName"]
        text = []
        for i, v in enumerate(message["data"]):
            if v["type"] in ["text", "link"] and v["content"]:
                content = json.loads(v["content"])
                text.append(content[0])
            elif v["type"] == "smile":
                k = f":{i}:"
                images[k] = v["smallUrl"]
                text.append(k)
            elif v["type"] == "mention":
                text.append(v["displayName"])
        MESSAGES.append(Message(text=" ".join(text), name=name, images=images))
