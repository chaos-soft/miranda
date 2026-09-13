from configparser import ConfigParser
import asyncio
import sys

from . import config
from . import server
from .common import (
    ModuleManager,
    RESTART_EVENT,
    SHUTDOWN_EVENT,
    get_config_file,
    logger,
    print_error,
)

MODULES: list[str] = [
    "goodgame",
    "twitch",
    "vkplay",
    "youtube",
]


class Application:
    config: ConfigParser
    config_mtime: float
    module_manager: ModuleManager
    modules: list[str]

    def __init__(self, config: ConfigParser, modules: list[str]):
        self.config = config
        self.config_mtime = get_config_file("config.ini").stat().st_mtime
        self.module_manager = ModuleManager()
        self.modules = modules

    async def main(self) -> None:
        current_task = asyncio.current_task()
        while not SHUTDOWN_EVENT.is_set():
            self.module_manager.init_modules(self.config, self.modules)
            self.module_manager.start()
            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.reload_config())
                    tg.create_task(self.restart_waiter())
                    tg.create_task(self.shutdown_waiter())
                    tg.create_task(server.Server().main())
            except* RestartError:
                tasks = []
                for task in asyncio.all_tasks():
                    if task != current_task:
                        tasks.append(task)
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(5)
            except* ShutdownError:
                pass
            except* Exception as e:
                logger.exception(e)
                raise

    async def reload_config(self) -> None:
        while True:
            await asyncio.sleep(5)
            mtime = get_config_file("config.ini").stat().st_mtime
            if mtime > self.config_mtime:
                self.config_mtime = mtime
                config.load()
                print_error("Обновился config.ini.")
                raise RestartError

    async def restart_waiter(self) -> None:
        await RESTART_EVENT.wait()
        RESTART_EVENT.clear()
        raise RestartError

    async def shutdown_waiter(self) -> None:
        await SHUTDOWN_EVENT.wait()
        raise ShutdownError


class RestartError(Exception):
    pass


class ShutdownError(Exception):
    pass


def main() -> int:
    app = Application(config.CONFIG, MODULES)
    try:
        asyncio.run(app.main())
    except KeyboardInterrupt:
        return 128 + 2
    except Exception as e:
        logger.exception(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
