"""
Email faking code for amzscout-scrape.

Copyright 2023 Parker Wahle <regulad@regulad.xyz>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied. See the License for the specific language governing
permissions and limitations under the License.

"""
from time import sleep
from uuid import uuid4

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By


def get_writeonly_tempemail(driver: WebDriver) -> str:
    """
    Get a clean email using selenium that shouldn't already have an account attached
    """
    old_tab = driver.current_window_handle

    driver.switch_to.new_window("tab")
    driver.get("https://temp-mail.org/en/")

    while "Loading" in driver.find_element(By.ID, "mail").get_attribute("value"):
        sleep(0.1)

    email = driver.find_element(By.ID, "mail").get_attribute("value")

    driver.close()
    driver.switch_to.window(old_tab)

    return email


def get_readable_tempemail(driver: WebDriver) -> str:
    """
    Use a legit email service to get a clean email
    """
    raise NotImplementedError


def get_random_plausible_email(driver: WebDriver, *, domain: str = "gmail.com") -> str:
    """
    Get a random clean email that shouldn't already have an account attached
    """
    # Slight problem: AMZScout seems to have been detecting our scraping and is now locking out every
    # non-gmail email. It's their fault for not using email verification & a captcha!

    # I got around this by cycling my IP address, but we need some better type of proxy to avoid getting kneecapped
    # in the future. Check out my project regulad/sticky-starfish
    username = uuid4().hex
    short_username = username[: int(len(username) // 4)]
    email = f"{short_username}@{domain}"
    return email


__all__ = ["get_random_plausible_email", "get_writeonly_tempemail", "get_readable_tempemail"]
