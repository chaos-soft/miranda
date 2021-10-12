from typing import Any

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

import common

DRIVER: Any = webdriver.Remote(desired_capabilities=DesiredCapabilities.FIREFOX)


class Chat(common.Commands):
    driver = DRIVER
    element: str = '/html/body/div/div[3]/div[4]/gg-feed-ctrl/div[3]/div/div[1]/div[2]/div/div[3]/div[2]/div[2]/div/ng-transclude/div'  # noqa: E501

    def process_element(self, element: Any) -> None:
        if element.get_attribute('className') == 'message-block ':
            super().process_element(element)

    def render_element(self, element: Any) -> None:
        common.MESSAGES.append(element.get_attribute('outerHTML').replace(
                               '"/', '"https://goodgame.ru/'))


class Play(common.Play):
    driver = DRIVER
    element: str = '//*[@id="_bigPlayBtn"]'

    def process_element(self, element: Any) -> None:
        element.click()


class Viewers(common.Viewers):
    driver = DRIVER
    element: str = '/html/body/div/div[2]/section/gg-main-scroll/div/div[1]/div[2]/div/div/div/div/div[1]/div/div/div[3]/div[1]/div/div[2]/div[3]/span/span[2]'  # noqa: E501
    id: str = 'g'


def close_driver() -> None:
    DRIVER.close()
