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
import zipfile
from enum import Enum, auto
from pathlib import Path
from typing import Any, Type, cast
from urllib.parse import urlparse

from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.chromium.webdriver import ChromiumDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.webdriver import WebDriver as EdgeDriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxDriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from undetected_chromedriver import Chrome as uChromeDriver
from undetected_chromedriver import ChromeOptions as uChromeOptions

from . import AmzscoutscrapeAssets
from .email import get_random_plausible_email
from .proxy import ip_of
from .utils import retry, reverse_map

logger = logging.getLogger(__package__)
EXTENSION = AmzscoutscrapeAssets.path("extensions", "extension_2_4_3_4.crx")
EXTENSION_ID = "njopapoodmifmcogpingplfphojnfeea"
EXPLICIT_IMPLICIT_WAIT = 30


class Driver(Enum):
    CHROME = auto()
    U_CHROME = auto()
    EDGE = auto()
    FIREFOX = auto()


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
    driver_type: Driver = Driver.U_CHROME,
    timeout: float | None = 60.0,
    proxy: None | str = None,
    load_extension: bool = True,
) -> WebDriver:
    """
    Initialize a driver with the given options.
    """

    # windows registry key: Software\Policies\Google\Chrome\BackgroundModeEnabled
    # WHY CAN THIS NOT BE DISABLED WITH A SWITCH
    # WHY DOES IT HAVE TO BE A REGISTRY KEY
    # FUCK YOU GOOGLE

    if os.name == "nt" and driver_type is Driver.U_CHROME:
        import ctypes
        import winreg

        # https://admx.help/?Category=Chrome&Policy=Google.Policies.Chrome::BackgroundModeEnabled
        WIN_REGISTRY_SCOPE = winreg.HKEY_CURRENT_USER
        WIN_REGISTRY_VALUE_NAME = r"BackgroundModeEnabled"
        WIN_REGISTRY_VALUE_TYPE = winreg.REG_DWORD

        if ctypes.windll.shell32.IsUserAnAdmin():
            logger.warning(
                "You are running on windows. "
                "We are going to attempt to make a registry modification so the headless chrome does not "
                "continue as a background process after UC is closed."
            )
            try:
                registry_key = winreg.CreateKeyEx(
                    WIN_REGISTRY_SCOPE, r"Software\Policies\Google\Chrome", 0, winreg.KEY_WRITE
                )
                current_value = cast(
                    int, winreg.QueryValueEx(registry_key, WIN_REGISTRY_VALUE_NAME)
                )
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
        else:
            logger.warning(
                "You are running on Windows. There is a known bug with headless chrome and undetected_chromedriver "
                "that can cause it start in Background Mode and not close when UC is closed. "
                "The solution is a registry modification, but we do not have the rights to change the registry."
            )

    if driver_type is not Driver.FIREFOX:
        options_class: Type[ChromiumOptions]
        match driver_type:
            case Driver.CHROME:
                options_class = ChromeOptions
            case Driver.U_CHROME:
                options_class = uChromeOptions
            case Driver.EDGE:
                options_class = EdgeOptions
            case _:
                options_class = ChromiumOptions

        options: ChromiumOptions = options_class()

        # need to unpack the extension
        if load_extension:
            extension_folder = Path(tempfile.gettempdir()).joinpath(
                f"chromium_extension_{EXTENSION_ID}"
            )
            # no shot something else uses this
            if not extension_folder.exists():
                extension_folder.mkdir()
                with zipfile.ZipFile(EXTENSION) as zip_file:
                    zip_file.extractall(extension_folder)
            options.add_argument(f"--load-extension={extension_folder}")

        # we aren't loading the proxy from geonode rn because it's way way way too slow
        if proxy is not None:
            logger.info(f"Proxy {proxy} found for Chromium.")
            options.add_argument(f"""--proxy-server={proxy}""")

        driver_kwargs: dict[str, Any] = {"options": options}

        # headless support
        match driver_type:
            case Driver.EDGE:
                if headless:
                    logger.warning("Headless mode is not supported for Edge. Ignoring.")
            case Driver.U_CHROME:
                driver_kwargs["headless"] = headless
                driver_kwargs["use_subprocess"] = False
            case Driver.CHROME | _:
                options.add_argument("--headless")

        driver_class: Type[ChromiumDriver]
        match driver_type:
            case Driver.CHROME:
                driver_class = ChromeDriver
            case Driver.U_CHROME:
                driver_class = uChromeDriver
            case Driver.EDGE:
                driver_class = EdgeDriver
            case _:
                driver_class = ChromiumDriver

        driver: WebDriver = driver_class(**driver_kwargs)
    else:
        options: FirefoxOptions = FirefoxOptions()
        options.headless = headless

        # Copilot wrote all of this: I have NO idea if it works
        if proxy is not None:
            logger.info(f"Proxy {proxy} found for Firefox.")
            options.set_preference("network.proxy.type", 1)
            options.set_preference("network.proxy.http", proxy)
            options.set_preference("network.proxy.http_port", 80)
            options.set_preference("network.proxy.ssl", proxy)
            options.set_preference("network.proxy.ssl_port", 80)

        if load_extension:
            raise NotImplementedError("Firefox extension loading not supported yet.")

        driver: WebDriver = FirefoxDriver(options=options)

    if timeout is not None:
        driver.implicitly_wait(timeout)
        driver.set_page_load_timeout(timeout)
        driver.set_script_timeout(timeout)
    else:
        driver.implicitly_wait(EXPLICIT_IMPLICIT_WAIT)  # not set by default

    driver_name = str(driver)
    if isinstance(driver, ChromiumDriver):
        driver_name = f"Driver {driver.service.process.pid}"
    logger.info(f"{driver_name} started successfully.")

    return driver


@retry(tries=3, backoff_seconds=2)
def create_fresh_driver(
    headless: bool = True,
    driver_type: Driver = Driver.U_CHROME,
    timeout: float | None = 60.0,
    proxy: None | str = None,
    load_extension: bool = True,
) -> WebDriver:
    """
    Create a fresh driver with the given options.
    """

    driver = _init_driver(headless, driver_type, timeout, proxy, load_extension)
    timeout = timeout or EXPLICIT_IMPLICIT_WAIT
    wait = WebDriverWait(driver, timeout)

    try:
        # When AMZScout PRO extension first loads in, it does this weird thing where it opens a new tab and then closes it.
        if load_extension:
            wait.until(lambda d: len(d.window_handles) == 2)
            web_map = identify_websites(driver)

            amazon_tab = reverse_map(web_map, "www.amazon.com")
            chrome_start_tab = reverse_map(web_map, "welcome")
            del web_map

            driver.switch_to.window(amazon_tab)
            del amazon_tab  # irrelevant
        else:
            chrome_start_tab = driver.current_window_handle
            driver.switch_to.new_window("tab")

        # This will be the email we use to sign up for our account
        email = get_random_plausible_email(driver)

        if load_extension:
            # We will use the extension to bring us to the "sign up for an account" page
            driver.find_element(By.CLASS_NAME, "login-btn").click()
        else:
            driver.get("https://amzscout.net/app/#/auth/login")

            # now we get the iframe
            # for some reason no matter what I do Selenium will never focus on this iframe
            # so we brute force!
            wait.until(ec.presence_of_element_located((By.TAG_NAME, "iframe")))
            iframe = driver.find_element(By.TAG_NAME, "iframe")
            iframe_url = iframe.get_attribute("src")
            del iframe  # this reference is about to be stale, so delete it now so we cant shoot ourselves in the foot
            driver.get(iframe_url)

        # Type in email
        driver.find_element(By.TAG_NAME, "input").send_keys(email)
        # Sign up dialog
        wait.until(ec.element_to_be_clickable((By.CLASS_NAME, "PgAuth-Sign-form__btn")))
        driver.find_element(By.CLASS_NAME, "PgAuth-Sign-form__btn").click()

        # check for "The email address is already registered."
        if ec.visibility_of_any_elements_located((By.CLASS_NAME, "PgAuth-Error"))(driver):
            ip = "<unknown>"
            try:
                ip = ip_of(proxy)
            except Exception:
                pass

            raise RuntimeError(f"Email {email} and/or IP {ip} could blocked.")
            # retry in case of a IP ban which also manifests as this

        # Wait for the destination page to load, which is different depending on whether we're using the extension
        if load_extension:
            wait.until(ec.url_contains("amazon.com"))
            # back @ amazon, skip the tutorial
            driver.find_element(By.CLASS_NAME, "seller-tips__modal-skip-btn").click()
        else:
            # redirects in 3 seconds
            # wait.until(ec.url_matches("https://amzscout.net/app/#/database"))
            # doesn't work, lets do it ourselves
            wait.until(
                ec.visibility_of_all_elements_located((By.CLASS_NAME, "PgAuth-Progress__title"))
            )
            countdown = driver.find_elements(By.CLASS_NAME, "PgAuth-Progress__title")[1]
            wait.until(lambda _: "0" in countdown.text)
            # skip the tutorial
            driver.get("https://amzscout.net/app/#/database")
            # "Welcome to AMZScout!"
            wait.until(ec.element_to_be_clickable((By.CLASS_NAME, "custom-tour-class__btn")))
            driver.find_element(By.CLASS_NAME, "custom-tour-class__btn").click()
            # "Welcome to AMZScout!"
            wait.until(ec.element_to_be_clickable((By.CLASS_NAME, "custom-tour-class__btn")))
            driver.find_element(By.CLASS_NAME, "custom-tour-class__btn").click()
            # "TRY PRO EXTENSION FOR FREE"
            wait.until(ec.element_to_be_clickable((By.CLASS_NAME, "pro-ad__close")))
            driver.find_element(By.CLASS_NAME, "pro-ad__close").click()
            # "GET UP TO 10 READY-TO-GO PRODUCTS" (banner ad)
            wait.until(ec.element_to_be_clickable((By.CLASS_NAME, "banner__close")))
            driver.find_element(By.CLASS_NAME, "banner__close").click()

        # Clean it up
        driver.close()
        driver.switch_to.window(chrome_start_tab)
        del chrome_start_tab  # irrelevant
    except Exception:
        driver.quit()
        raise
    else:
        driver_name = str(driver)
        if isinstance(driver, ChromiumDriver):
            driver_name = f"Driver {driver.service.process.pid}"
        logger.info(f"{driver_name} configured successfully. Ready.")
        return driver


__all__ = ("create_fresh_driver",)
