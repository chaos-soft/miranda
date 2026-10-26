from datetime import datetime
from urllib.parse import quote_plus
import asyncio

from .chat import Chat, OAuth, WebSocket
from .common import (
    D,
    MESSAGES,
    MessageABC,
    MessageMiranda,
    STATS,
    create_task,
    make_request,
)
from .config import CONFIG

CLIENT_ID: str = "g0qvsrztagks1lbg03kwnt67pg9x8a5"
CLIENT_SECRET: str = "krlzbgo35j454d6aoxemjmnjifeoi9"
FOLLOWS: dict[str, int] = {}
SCOPES: list[str] = ["chat:read", "moderator:read:followers"]
TIMEOUT_10S: int = 10
TIMEOUT_30S: int = 30
TIMEOUT_5M: int = 5 * 60


async def start() -> None:
    channel = CONFIG["twitch"].get("channel", "")
    oauth = OAuthTwitch(channel)
    create_task(oauth.main())
    await oauth.credentials_event.wait()
    create_task(Twitch(channel, oauth).main())
    if CONFIG["twitch"].getboolean("is_follows"):
        create_task(TwitchFollows(channel, oauth).main())
    if CONFIG["twitch"].getboolean("is_stats"):
        create_task(TwitchStats(channel, oauth).main())


class Message(MessageABC):
    color: str = ""
    id = "t"
    timestamp: int = 0

    def to_dict(self) -> D:
        d = super().to_dict()
        d["color"] = self.color
        return d


class OAuthTwitch(OAuth):
    authorization_url: str = "https://id.twitch.tv/oauth2/authorize"
    file_name: str = "twitch.json"
    lock: asyncio.Lock
    state: str = "twitch-xxx"
    token_url: str = "https://id.twitch.tv/oauth2/token"

    def __init__(self, channel: str) -> None:
        super().__init__(channel)
        self.lock = asyncio.Lock()

    async def get_authorization_url(self) -> None:
        if self.credentials_event.is_set() or CONFIG["twitch"]["code"]:
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
                "&scope=",
                quote_plus(" ".join(SCOPES)),
                "&state=",
                self.state,
            ]
        )
        text = f'<a href="{url}">Авторизация в Twitch</a>.'
        MESSAGES.append(MessageMiranda(text=text))

    async def get_credentials(self) -> None:
        if self.credentials_event.is_set() or not CONFIG["twitch"]["code"]:
            return None
        await self.on_start("get_credentials()")
        while True:
            data = {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": CONFIG["twitch"]["code"],
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            }
            d = await make_request(self.token_url, method="POST", data=data)
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
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": self.credentials["refresh_token"],
            }
            data = await make_request(self.token_url, method="POST", data=data)
            if data:
                self.credentials = data
                self.dump_credentials()

    def get_headers(self) -> dict[str, str]:
        return {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {self.credentials['access_token']}",
        }


class Twitch(WebSocket):
    keys: list[str] = ["color", "emotes", "display-name", "user-id", "system-msg"]
    oauth: OAuthTwitch
    url: str = "wss://irc-ws.chat.twitch.tv"

    def __init__(self, channel: str, oauth: OAuthTwitch) -> None:
        super().__init__(channel)
        self.oauth = oauth

    async def on_message(self, data: str) -> None:
        if "PRIVMSG" in data:
            self.add_message(self.parse_data(data))
        elif "USERNOTICE" in data:
            self.add_notify(self.parse_data(data))
        elif data.startswith("PING"):
            await self.send_pong(data)

    async def on_open(self) -> None:
        assert self.w is not None
        # PASS и NICK именно в таком порядке.
        await self.w.send(f"PASS oauth:{self.oauth.credentials['access_token']}\r\n")
        await self.w.send("NICK chaos-soft\r\n")
        await self.w.send("CAP REQ :twitch.tv/tags twitch.tv/commands\r\n")
        await self.w.send(f"JOIN #{self.channel}\r\n")

    async def send_pong(self, data: str) -> None:
        assert self.w is not None
        await self.w.send(f'{data.replace("PING", "PONG")}\r\n')

    def add_message(self, message: D) -> None:
        if message["user-id"] in FOLLOWS:
            message["timestamp"] = FOLLOWS[message["user-id"]]
        message.pop("user-id")
        message["name"] = message.pop("display-name")
        self.parse_emotes(message)
        MESSAGES.append(Message(**message))

    def add_notify(self, message: D) -> None:
        text = CONFIG["twitch"]["text"].format(
            message["system-msg"].replace(r"\s", " ")
        )
        MESSAGES.append(MessageMiranda(text=text, is_event=True))

    def clean_text(self, text: str) -> str:
        """Очищает от /me."""
        return text[8:-1] if text.startswith("\x01") else text

    def parse_data(self, data: str) -> D:
        parts = data.split(" ", 4)
        message = {}
        if len(parts) == 5:
            message["text"] = self.clean_text(parts[4][1:])
        for part in parts[0].split(";"):
            k, v = part.split("=")
            if v and k in self.keys:
                message[k] = v
        return message

    def parse_emotes(self, message: D) -> None:
        if "emotes" not in message:
            return None
        images = {}
        for emote in message["emotes"].split("/"):
            id, indexes = emote.split(":")
            indexes = indexes.split(",", 1)[0].split("-")
            k = message["text"][int(indexes[0]) : int(indexes[1]) + 1]
            images[k] = (
                f"https://static-cdn.jtvnw.net/emoticons/v2/{id}/static/light/1.0"
            )
        message.pop("emotes")
        message["images"] = dict(
            sorted(images.items(), key=lambda v: len(v[0]), reverse=True)
        )


class TwitchFollows(Chat):
    is_first_run: bool = True
    oauth: OAuthTwitch
    params: D = {"first": 100, "broadcaster_id": None}
    # https://dev.twitch.tv/docs/api/reference/#get-channel-followers
    url: str = "https://api.twitch.tv/helix/channels/followers"

    def __init__(self, channel: str, oauth: OAuthTwitch) -> None:
        super().__init__(channel)
        self.oauth = oauth

    async def get_channel_id(self) -> str:
        # https://dev.twitch.tv/docs/api/reference/#get-users
        url = f"https://api.twitch.tv/helix/users?login={self.channel}"
        while True:
            data = await make_request(url, headers=self.oauth.get_headers())
            if data:
                channel_id = data["data"][0]["id"]
                return channel_id
            else:
                await self.oauth.refresh_credentials()

    async def load(self) -> int:
        data = await make_request(
            self.url,
            params=self.params,
            headers=self.oauth.get_headers(),
        )
        if not data:
            await self.oauth.refresh_credentials()
            return TIMEOUT_10S
        for follow in data["data"]:
            if follow["user_id"] in FOLLOWS:
                break
            FOLLOWS[follow["user_id"]] = int(
                datetime.strptime(
                    follow["followed_at"].split("T")[0], "%Y-%m-%d"
                ).timestamp(),
            )
            if not self.is_first_run:
                self.alert(follow)
        if not self.is_first_run:
            return TIMEOUT_5M

        follows_limit = CONFIG["twitch"].getint("follows_limit", 0)
        if len(FOLLOWS) < follows_limit and len(FOLLOWS) != data["total"]:
            self.params["after"] = data["pagination"]["cursor"]
            return TIMEOUT_10S
        else:
            self.params.pop("after", None)
            self.params["first"] = 10
            self.is_first_run = False
            self.print_error(f"всего фолловеров: {data['total']}.")
            self.print_error(f"загруженно фолловеров: {follows_limit}.")
            return TIMEOUT_5M

    async def main(self) -> None:
        channel_id = await self.get_channel_id()
        await self.on_start()
        self.params["broadcaster_id"] = channel_id
        if self.params["first"] > CONFIG["twitch"].getint("follows_limit"):
            self.params["first"] = CONFIG["twitch"].getint("follows_limit")
        try:
            while True:
                sleep = await self.load()
                await asyncio.sleep(sleep)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    def alert(self, follow: dict[str, str]) -> None:
        text = CONFIG["twitch"]["text_follower"].format(
            follow["user_name"] or follow["user_login"]
        )
        MESSAGES.append(MessageMiranda(text=text, is_event=True))


class TwitchStats(Chat):
    oauth: OAuthTwitch
    url: str = "https://api.twitch.tv/helix/streams?user_login={}&first=1"

    def __init__(self, channel: str, oauth: OAuthTwitch) -> None:
        super().__init__(channel)
        self.oauth = oauth
        self.url = self.url.format(channel)

    async def load(self) -> None:
        data = await make_request(self.url, headers=self.oauth.get_headers())
        if data:
            self.alert(data["data"][0]["viewer_count"] if data["data"] else "")
        else:
            await self.oauth.refresh_credentials()

    async def main(self) -> None:
        await self.on_start()
        try:
            while True:
                await self.load()
                await asyncio.sleep(TIMEOUT_30S)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    def alert(self, v: str) -> None:
        STATS["t"] = v
