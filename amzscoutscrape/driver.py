"""
Driver handing code for amzscout-scrape.

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
import logging
from pathlib import Path
from time import sleep
from typing import Any
from urllib.parse import urlparse

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.common.by import By
from undetected_chromedriver import Chrome as uChrome
from undetected_chromedriver import ChromeOptions as uChromeOptions

from . import AmzscoutscrapeAssets
from .proxy import fetch_working_proxy
from .utils import reverse_map

logger = logging.getLogger(__package__)
EXTENSION = AmzscoutscrapeAssets.path("extensions", "extension_2_4_3_4")


def identify_websites(driver: WebDriver) -> dict[str, str]:
    current_window = driver.current_window_handle
    web_map = dict()

    for window_handle in driver.window_handles:
        driver.switch_to.window(window_handle)
        url = urlparse(driver.current_url)
        web_map[window_handle] = url.netloc

    # Switch to the old tab
    driver.switch_to.window(current_window)

    return web_map


def get_clean_driver(headless: bool = True, undetected: bool = True) -> WebDriver:
    logger.info("Creating driver...")
    options: ChromiumOptions = (uChromeOptions if undetected else Options)()
    options.add_argument(f"--load-extension={EXTENSION}")

    # we aren't loading the proxy rn because it's way way way too slow
    # proxy = fetch_working_proxy()
    # options.add_argument(f"""--proxy-server={proxy}""")

    driver_kwargs: dict[str, Any] = {"options": options}

    if undetected:
        driver_kwargs["headless"] = headless
        driver_kwargs["use_subprocess"] = False
    elif headless:
        options.add_argument("--headless")

    driver: WebDriver = (uChrome if undetected else WebDriver)(**driver_kwargs)
    driver.implicitly_wait(30)

    logger.info(f"Driver {driver.service.process.pid} started successfully.")

    # Driver ready. Extension initialization.
    # Switch to the new tab

    while len(driver.window_handles) < 2:
        sleep(0.1)
    web_map = identify_websites(driver)

    amazon_tab = reverse_map(web_map, "www.amazon.com")
    chrome_start_tab = reverse_map(web_map, "welcome")
    del web_map

    # Ok, so this is dumb. We are going to make a temp email and use that to sign up.
    # Normally, there are a million websites for this. But we, we don't buy services. WE DO SOME SCRAPING!
    driver.switch_to.new_window("tab")
    driver.get("https://temp-mail.org/en/")

    while "Loading" in driver.find_element(By.ID, "mail").get_attribute("value"):
        sleep(0.1)

    email = driver.find_element(By.ID, "mail").get_attribute("value")

    driver.close()

    # Login!

    driver.switch_to.window(amazon_tab)
    del amazon_tab  # irrelevant

    driver.find_element(By.CLASS_NAME, "login-btn").click()
    # We will now be redirected to the login page
    driver.find_element(By.TAG_NAME, "input").send_keys(email)
    del email  # We don't need this anymore
    driver.find_element(By.CLASS_NAME, "PgAuth-Sign-form__btn").click()
    while "amazon" not in urlparse(driver.current_url).hostname.split("."):  # type: ignore
        sleep(0.1)
    # back @ amazon, skip the tutorial
    driver.find_element(By.CLASS_NAME, "seller-tips__modal-skip-btn").click()

    # Clean it up
    driver.close()
    driver.switch_to.window(chrome_start_tab)
    del chrome_start_tab  # irrelevant

    logger.info(f"Driver {driver.service.process.pid} configured successfully. Ready.")
    return driver


__all__ = ("get_clean_driver",)
