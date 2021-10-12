from datetime import datetime
from typing import Any, Union
import threading
import time

from selenium.common.exceptions import NoSuchElementException

from config import CONFIG

COMMANDS: dict[str, list[str]] = {}
MESSAGES: list[str] = []
STATS: dict[str, Union[str]] = {}

for k in CONFIG['commands']:
    # {'-x': ['имя метода', 'права']}
    COMMANDS[k] = CONFIG['commands'].getlist(k)


class Base(threading.Thread):
    def on_start(self) -> None:
        self.print_error('OK')

    def on_stop(self) -> None:
        self.print_error('TERMINATED')

    def print_error(self, str_: str) -> None:
        print_error(f'{type(self).__name__} / {str_}')

    def stop(self) -> None:
        self.join()


class WebDriver(Base):
    driver: Any = None
    element: str = ''
    is_stop: bool = False

    def __init__(self, url: str) -> None:
        self.driver.get(url)
        self.url = url
        super().__init__()

    def find_element_by_xpath(self, element: str) -> Any:
        while not self.is_stop:
            try:
                return self.driver.find_element_by_xpath(element)
            except NoSuchElementException:
                time.sleep(2)

    def print_error(self, str_: str) -> None:
        print_error(f'{type(self).__name__} ({self.url}) / {str_}')

    def stop(self) -> None:
        self.is_stop = True
        super().stop()


class Chat(WebDriver):
    def process_element(self, element: Any) -> None:
        self.render_element(element)

    def render_element(self, element: Any) -> None:
        MESSAGES.append(element.get_attribute('outerHTML'))

    def run(self) -> None:
        element = self.find_element_by_xpath(self.element)
        self.on_start()
        last = []
        while not self.is_stop:
            messages = element.find_elements_by_xpath('./*')[-10:]
            for message in messages:
                if message not in last:
                    last.append(message)
                    self.process_element(message)
            last = last[-10:]
            time.sleep(2)
        self.on_stop()


class Commands(Chat):
    friendly: list[str] = CONFIG['base'].getlist('friendly')
    root: str = CONFIG['base'].get('root')

    def add_image(self, element: Any) -> None:
        try:
            a = element.find_elements_by_tag_name('a')[-1]
            url = a.get_attribute('href')
            if url[-3:] not in ['jpg', 'png']:
                raise Exception
            MESSAGES.append(element.get_attribute('outerHTML').replace(
                            a.get_attribute('outerHTML'), f'<img src="{url}">'))
        except (Exception, IndexError):
            super().process_element(element)

    def clean_chat(self, *args: Any) -> None:
        MESSAGES.append('clean_chat')

    def clean_messages(self, *args: Any) -> None:
        MESSAGES[:] = []
        self.clean_chat()

    def is_access(self, text: str, params: list[str]) -> bool:
        if text.startswith(self.root):
            return True
        elif params[1] == 'friendly':
            for name in self.friendly:
                if text.startswith(name):
                    return True
        return False

    def process_element(self, element: Any) -> None:
        text = str.lstrip(element.get_attribute('textContent'))
        for k, p in COMMANDS.items():
            if k in text:
                if self.is_access(text, p):
                    getattr(self, p[0])(element)
                    return None
        super().process_element(element)


class Play(WebDriver):
    def process_element(self, element: Any) -> None:
        raise NotImplementedError

    def run(self) -> None:
        element = self.find_element_by_xpath(self.element)
        self.on_start()
        self.process_element(element)


class Viewers(WebDriver):
    id: str = ''

    def process_element(self, element: Any) -> None:
        STATS[self.id] = element.get_attribute('textContent')

    def run(self) -> None:
        element = self.find_element_by_xpath(self.element)
        self.on_start()
        while not self.is_stop:
            self.process_element(element)
            time.sleep(5)
        self.on_stop()


def print_error(e: str) -> None:
    text = f'{str(datetime.now()).split(".")[0]} / {e}'
    MESSAGES.append(text)
    print(text)
