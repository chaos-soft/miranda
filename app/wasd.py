from typing import Any

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

import common

DRIVER: Any = webdriver.Remote(desired_capabilities=DesiredCapabilities.FIREFOX)


class Chat(common.Commands):
    driver = DRIVER
    element: str = '/html/body/wasd-root/div[2]/div/wasd-channel/div/div[2]/wasd-chat-wrapper/div[2]/div[2]/div/wasd-chat/div/wasd-chat-body/div/wasd-chat-messages/div/div/div'  # noqa: E501

    def process_element(self, element: Any) -> None:
        try:
            element = element.find_element_by_class_name('message__info__text')
        except NoSuchElementException:
            pass
        super().process_element(element)


class Play(common.Play):
    driver = DRIVER
    element: str = '/html/body/wasd-root/div[2]/div/wasd-channel/div/div[1]/div/div[1]/div[2]/wasd-player/div/div[2]/wasd-player-component/div/div[2]/div[2]/div[2]/div/div[1]/button'  # noqa: E501

    def process_element(self, element: Any) -> None:
        if element:
            element.click()


class Viewers(common.Viewers):
    driver = DRIVER
    element: str = '/html/body/wasd-root/div[2]/div/wasd-channel/div/div[1]/div/div[1]/div[1]/wasd-player-info/div/div/div/div[2]/div[2]/div/div/div[1]/div'  # noqa: E501
    id: str = 'w'

    def process_element(self, element: Any) -> None:
        common.STATS[self.id] = ''.join(filter(str.isdigit, element.get_attribute('textContent')))


def close_driver() -> None:
    DRIVER.close()
