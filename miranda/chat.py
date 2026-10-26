from abc import ABCMeta, abstractmethod
import asyncio
import json

import websockets  # type: ignore

from .common import D, get_config_file, print_error


class Base(metaclass=ABCMeta):
    async def on_close(self) -> None:
        self.print_error("остановлен.")

    async def on_start(self, str_: str = "") -> None:
        if str_:
            self.print_error(f"{str_} запущен.")
        else:
            self.print_error("запущен.")

    def print_error(self, str_: str) -> None:
        print_error(f"{type(self).__name__} {str_}")

    def print_exception(self, e: Exception) -> None:
        self.print_error(f"{type(e).__name__}: {e}")


class Chat(Base):
    channel: str

    def __init__(self, channel: str) -> None:
        self.channel = channel

    def print_error(self, str_: str) -> None:
        print_error(f"{type(self).__name__} ({self.channel}) {str_}")


class OAuth(Chat):
    credentials: D
    credentials_event: asyncio.Event
    file_name: str
    redirect_uri: str = "http://localhost:5173"
    state: str

    def __init__(self, channel: str) -> None:
        super().__init__(channel)
        self.credentials_event = asyncio.Event()
        self.load_credentials()

    def delete_credentials_file(self) -> None:
        get_config_file(self.file_name).unlink()

    def dump_credentials(self) -> None:
        with get_config_file(self.file_name).open("w") as f:
            json.dump(self.credentials, f)

    def load_credentials(self) -> None:
        try:
            with open(get_config_file(self.file_name)) as f:
                self.credentials = json.load(f)
            if self.credentials:
                self.credentials_event.set()
        except FileNotFoundError:
            self.credentials = {}
            self.dump_credentials()


class WebSocket(Chat):
    heartbeat_data: str
    url: str
    w: websockets.ClientConnection | None = None

    async def main(self) -> None:
        try:
            async for self.w in websockets.connect(self.url):
                try:
                    await self.on_start()
                    await self.on_open()
                    async for message in self.w:
                        await self.on_message(str(message).strip())
                except websockets.ConnectionClosed as e:
                    self.print_exception(e)
                    await self.on_close()
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            await self.on_close()
            raise

    async def on_close(self) -> None:
        if self.w:
            await self.w.close()
        self.w = None
        await super().on_close()

    @abstractmethod
    async def on_message(self, data_str: str) -> None:
        pass

    async def on_open(self) -> None:
        pass

    async def send_heartbeat(self) -> None:
        if self.w:
            try:
                await self.w.send(self.heartbeat_data)
            except websockets.ConnectionClosed:
                pass
