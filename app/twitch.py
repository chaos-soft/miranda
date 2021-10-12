from typing import Any

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys

import common

DRIVER: Any = webdriver.Remote(desired_capabilities=DesiredCapabilities.FIREFOX)


class Chat(common.Commands):
    driver = DRIVER
    element: str = '//div[contains(@class, "chat-scrollable-area__message-container")]'

    def process_element(self, element: Any) -> None:
        try:
            element = element.find_element_by_class_name('chat-line__no-background')
        except NoSuchElementException:
            pass
        super().process_element(element)


class Play(common.Play):
    driver = DRIVER
    element: str = '/html'

    def process_element(self, element: Any) -> None:
        element.send_keys(Keys.SPACE)


class Viewers(common.Viewers):
    driver = DRIVER
    element: str = '/html/body/div[1]/div/div[2]/div[1]/main/div[2]/div[3]/div/div/div[1]/div[1]/div[2]/div/div[1]/div/div/div/div[2]/div[2]/div[2]/div/div/div[1]/div[1]/div/p/span'  # noqa: E501
    id: str = 't'


def close_driver() -> None:
    DRIVER.close()
