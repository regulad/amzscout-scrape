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
import os
import tempfile
import time
import winreg
import zipfile
from pathlib import Path
from time import sleep
from typing import Any, cast
from urllib.parse import urlencode, urlparse

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.common.by import By
from undetected_chromedriver import Chrome as uChrome
from undetected_chromedriver import ChromeOptions as uChromeOptions

from . import AmzscoutscrapeAssets
from .email import get_random_plausible_email
from .utils import reverse_map

logger = logging.getLogger(__package__)
EXTENSION = AmzscoutscrapeAssets.path("extensions", "extension_2_4_3_4.crx")
EXTENSION_ID = "njopapoodmifmcogpingplfphojnfeea"

# https://admx.help/?Category=Chrome&Policy=Google.Policies.Chrome::BackgroundModeEnabled
WIN_REGISTRY_SCOPE = winreg.HKEY_CURRENT_USER
WIN_REGISTRY_VALUE_NAME = r"BackgroundModeEnabled"
WIN_REGISTRY_VALUE_TYPE = winreg.REG_DWORD


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


def _init_driver(
    headless: bool = True,
    undetected: bool = True,
    timeout: float = 60.0,
    proxy: None | str = None,
) -> WebDriver:
    """
    Initialize a driver with the given options.
    """

    # windows registry key: Software\Policies\Google\Chrome\BackgroundModeEnabled
    # WHY CAN THIS NOT BE DISABLED WITH A SWITCH
    # WHY DOES IT HAVE TO BE A REGISTRY KEY
    # FUCK YOU GOOGLE

    if os.name == "nt" and headless and undetected:
        # TODO: Maybe undo this after we are done?
        logger.warning(
            "You are running on windows. "
            "We are going to attempt to make a registry modification so the headless chrome does not "
            "continue as a background process after UC is closed."
        )
        try:
            registry_key = winreg.CreateKeyEx(
                WIN_REGISTRY_SCOPE, r"Software\Policies\Google\Chrome", 0, winreg.KEY_WRITE
            )
            current_value = cast(int, winreg.QueryValueEx(registry_key, WIN_REGISTRY_VALUE_NAME))
            background_mode_enabled = True if current_value == 1 else 0
            if background_mode_enabled:
                winreg.SetValueEx(
                    WIN_REGISTRY_SCOPE, WIN_REGISTRY_VALUE_NAME, 0, WIN_REGISTRY_VALUE_TYPE, 0
                )
        except WindowsError as w_e:
            logger.exception(f"Unable to disable Background Mode: {w_e}")
            logger.warning("You may notice background chrome processes piling up.")
        finally:
            if "registry_key" in locals():
                winreg.CloseKey(registry_key)

    options: ChromiumOptions = (uChromeOptions if undetected else Options)()
    # need to unpack the extension
    extension_folder = Path(tempfile.gettempdir()).joinpath(f"chromium_extension_{EXTENSION_ID}")
    # no shot something else uses this
    if not extension_folder.exists():
        extension_folder.mkdir()
        with zipfile.ZipFile(EXTENSION) as zip_file:
            zip_file.extractall(extension_folder)
    options.add_argument(f"--load-extension={extension_folder}")

    # we aren't loading the proxy from geonode rn because it's way way way too slow
    if proxy is not None:
        logger.info(f"Proxy {proxy} found. Using.")
        options.add_argument(f"""--proxy-server={proxy}""")

    driver_kwargs: dict[str, Any] = {"options": options}

    if undetected:
        driver_kwargs["headless"] = headless
        driver_kwargs["use_subprocess"] = False
    elif headless:
        options.add_argument("--headless")

    driver: WebDriver = (uChrome if undetected else WebDriver)(**driver_kwargs)
    driver.implicitly_wait(timeout)
    driver.set_script_timeout(timeout)

    logger.info(f"Driver {driver.service.process.pid} started successfully.")

    return driver


def create_fresh_driver(
    headless: bool = True,
    undetected: bool = True,
    timeout: float = 60.0,
    proxy: None | str = None,
) -> WebDriver:
    # We need to make sure we don't spend too long, otherwise something definitely crashed and we need to restart

    driver = _init_driver(headless, undetected, timeout, proxy)

    # Driver ready. Extension initialization.
    # Switch to the new tab

    # AMZScout will sometimes open a new tab, sometimes not. We need to wait for it to open a new tab.
    started_waiting_for_extension_tab_at = time.time()
    waited_so_far: float = 0.0
    while len(driver.window_handles) < 2 and waited_so_far < timeout:
        waited_so_far = time.time() - started_waiting_for_extension_tab_at
        sleep(0.1)
    if len(driver.window_handles) < 2:
        logger.warning(
            "AMZScout did not open a new tab. This is not expected behavior. Attempting to correct..."
        )
        # Let's just make it manually.
        driver.get(
            "https://www.amazon.com/s?" + urlencode({"k": "fleshlight"})
        )  # i may have an immature sense of humor
        driver.find_element(By.TAG_NAME, "os-circle").click()  # we have to manually open the menu

    web_map = identify_websites(driver)

    amazon_tab = reverse_map(web_map, "www.amazon.com")
    chrome_start_tab = reverse_map(web_map, "welcome")
    del web_map

    email = get_random_plausible_email(driver)

    # Login!

    driver.switch_to.window(amazon_tab)
    del amazon_tab  # irrelevant

    driver.find_element(By.CLASS_NAME, "login-btn").click()
    # We will now be redirected to the login page
    driver.find_element(By.TAG_NAME, "input").send_keys(email)
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


__all__ = ("create_fresh_driver",)
