from typing import Any

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

import common


class Chat(common.Commands):
    driver: Any = webdriver.Remote(desired_capabilities=DesiredCapabilities.FIREFOX)
    element: str = '/html/body/peka-app/div/div/chat-page/chat-common/chat-instance/div/div[2]/chat-messages-list-wrapper/chat-messages-list/div'  # noqa: E501

    def __del__(self) -> None:
        self.driver.close()

    def process_element(self, element: Any) -> None:
        if element.tag_name == 'chat-message-wrapper':
            super().process_element(element)
