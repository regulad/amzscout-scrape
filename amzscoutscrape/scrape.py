"""
Scraping code for amzscout-scrape.

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
import base64
import logging
from time import sleep, time
from urllib.parse import urlencode

from _csv import Writer
from bs4 import BeautifulSoup
from requests import Session as RequestsSession
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from .proxy import setup_proxy_for_requests
from .utils import deprecated

logger = logging.getLogger(__package__)


def search_and_write_amazon(
    driver: WebDriver,
    csv_writer: Writer,
    query: str,
    proxy: str | None = None,
    *,
    write_headers: bool = True,
    write_data: bool = True,
) -> None:
    """
    Search for a query and write the results to a CSV file.

    Args:
        driver:
        csv_writer:
        proxy:
        query:
        write_headers:
        write_data:

    Returns:

    """
    wait = WebDriverWait(driver, driver.timeouts.implicit_wait)
    # TODO: replace timeout dependent code with WebDriverWait
    timeout = driver.timeouts.implicit_wait
    logger.info(f"Searching for {query!r}...")

    driver.get("https://www.amazon.com/s?" + urlencode({"k": query}))
    amazon_window_handle = driver.current_window_handle

    # open the menu
    driver.find_element(By.TAG_NAME, "os-circle").click()

    # wait for the AMZScout implicitly
    (driver.find_element(By.TAG_NAME, "amzscout-pro").find_element(By.CLASS_NAME, "l-appwrap"))

    # delete that dumbass ad with ChatGPT lookin headass
    driver.execute_script(
        """
        let ad = document.getElementsByTagName("ad")[0];
        ad.parentNode.removeChild(ad); // do NOT return, it crashes selenium
    """
    )

    # get the AMZScout window (again) make sure we don't have a stale reference
    appwrap = driver.find_element(By.TAG_NAME, "amzscout-pro").find_element(
        By.CLASS_NAME, "l-appwrap"
    )

    # TODO: if we wanted to enable more headers or change any other options, we could do it here

    # no stale protection needed here
    if write_headers:
        # We need to get the column names so that DA will be easier
        header = appwrap.find_element(By.CLASS_NAME, "maintable-header")
        column_names: list[str] = []
        for i, col in enumerate(header.find_elements(By.CLASS_NAME, "ng-binding")):
            # i = 0: #
            # i = 1: Product Name

            # We need to inject our "thumbnail image" and "description"

            if i != 1:
                column_names.append(col.text)
            else:
                # this is the title column
                # special cases
                column_names.append("Thumbnail Image")
                column_names.append("Product Name")
                column_names.append("URL")
                column_names.append("Description")
                column_names.append("About this item")
                column_names.append("From the manufacturer")
        logger.info(f"Saving {len(column_names)} columns: {', '.join(column_names)}")
        csv_writer.writerow(column_names)

    if not write_data:
        return  # skip the rest of the function

    maintable = appwrap.find_element(By.CLASS_NAME, "maintable")

    # wait for the spinner(s) to go away
    spinner_wait_start = time()
    while True:
        # global spinner
        if "ng-hide" not in (
            driver.find_element(By.TAG_NAME, "amzscout-pro")
            .find_element(By.CLASS_NAME, "modals")
            .find_element(By.CSS_SELECTOR, "div.spinner.centered")
        ).get_attribute("class").split(" "):
            # the spinner not is hidden, we have to wait
            sleep(0.1)
            continue

        continue_nonlocal = False  # if we should continue the outer loop
        # local spinners
        for local_spinner in maintable.find_elements(By.TAG_NAME, "loader-spinner"):
            try:
                classes = local_spinner.get_attribute("class")  # should be "ng-hide" or ""
            except StaleElementReferenceException:
                # the spinner is gone, we have to wait
                continue_nonlocal = True
                break
            if "ng-hide" not in classes.split(" "):
                # the spinner not is hidden, we have to wait
                continue_nonlocal = True
                break
        if continue_nonlocal:
            sleep(0.1)
            continue

        break
    spinner_wait_end = time()
    spinner_wait_time = (
        spinner_wait_end - spinner_wait_start
    )  # this is the amount of time we have already waited
    dynamic_timeout = timeout * 2
    # this takes FOREVER to load, so we need to wait at least this much time
    if spinner_wait_time < dynamic_timeout:
        # we have waited less than the timeout, we should wait until more load in
        sleep(dynamic_timeout - spinner_wait_time)

    # From here on out, we are just screenscraping and don't need to click anything
    # To prevent stale element references, we are going to stop any currently running javascript
    driver.execute_script("window.stop();")

    with RequestsSession() as s:
        # initialize the session with data from the driver
        # s.cookies.update({c["name"]: c["value"] for c in driver.get_cookies()})  # unnecessary
        s.headers.update({"User-Agent": driver.execute_script("return navigator.userAgent")})
        setup_proxy_for_requests(s, proxy)
        # ok, lets scrape!
        rows_scraped = 0
        for i, row in enumerate(maintable.find_elements(By.CLASS_NAME, "maintable__row")):
            columns: list[str] = []
            try:
                for j, col in enumerate(row.find_elements(By.CLASS_NAME, "scout-col")):
                    if j < 2:  # skip the first two columns, they are not important
                        continue
                    # j = 2: number
                    # j = 3: title & image
                    try:
                        if j != 3:
                            columns.append(col.text)
                        else:
                            # column_names.append("Thumbnail Image")
                            try:
                                image_css = col.find_element(
                                    By.CSS_SELECTOR, "span.preview-img.ng-scope"
                                ).value_of_css_property("background-image")
                            except NoSuchElementException:
                                image_css = "none"
                            if image_css == "none":
                                image_b64 = ""
                            else:
                                # this will be something like 'url("https://m.media-amazon.com/images/I/71Pn98gmz3L._SL300_.jpg")'
                                image_url = image_css.split('"')[1]
                                # this will be something like 'https://m.media-amazon.com/images/I/71Pn98gmz3L._SL300_.jpg'
                                # we need to download the image and convert it to base64
                                image_response = s.get(image_url)
                                image_b64_string = base64.b64encode(image_response.content).decode(
                                    "utf-8"
                                )
                                image_b64 = f"data:{image_response.headers['Content-Type']};base64,{image_b64_string}"

                            columns.append(image_b64)

                            # column_names.append("Product Name")
                            a = col.find_element(By.CSS_SELECTOR, "a.ng-binding")
                            product_name = a.text

                            columns.append(product_name)

                            # column_names.append("URL")
                            short_url = a.get_attribute("href")

                            columns.append(short_url)

                            # OK, lets work on scraping the description & other data
                            # gotta fetch it with the full url
                            # i wanted to use requests & soup for this but it doesn't work perfect due to amazon's
                            # bot screening & the description being super odd & dynamic
                            logger.info(f"Deep scraping {product_name} ({short_url})...")
                            driver.switch_to.new_window("tab")
                            driver.get(short_url)
                            # while we are waiting for the page to road, we need to scratch out the AMZScout window
                            # since we just want the amazon page
                            driver.execute_script(
                                """
                                let ad = document.getElementsByTagName("amzscout-pro")[0];
                                ad.parentNode.removeChild(ad); // do NOT return, it crashes selenium
                            """
                            )
                            # lets try this:
                            soup = BeautifulSoup(
                                driver.page_source, "html.parser"
                            )  # page_source is the DOM, not the source

                            # column_names.append("Description")
                            description = soup.find("div", id="productDescription")
                            if description is not None:
                                columns.append(description.text.strip())
                            else:
                                columns.append("")  # null(?)

                            # column_names.append("About this item")
                            about = soup.find("div", id="feature-bullets")
                            if about is not None:
                                columns.append(about.text.strip())
                            else:
                                columns.append("")  # null(?)

                            # column_names.append("From the manufacturer")
                            manufacturer = soup.find("div", id="aplus")
                            if manufacturer is not None:
                                columns.append(manufacturer.text.strip())
                            else:
                                columns.append("")  # null(?)

                            logger.debug(f"Deep scraping {product_name} ({short_url})... done")
                            driver.close()
                            driver.switch_to.window(amazon_window_handle)
                            # we continue now
                    except StaleElementReferenceException as e:
                        logger.warning(
                            f"StaleElementReferenceException while scraping row {i} column {j}: {e}"
                        )
                        continue
            except StaleElementReferenceException as e:
                logger.warning(f"StaleElementReferenceException while scraping row {i}: {e}")
                continue
            csv_writer.writerow(columns)
            rows_scraped += 1

    logger.info(f"Scraped {rows_scraped} rows of data from query {query!r}")

    # we haven't the luxury of the "next 20 pages" button, so our results may be polluted by the only top 50 results we
    # get only being the best of the best


AMZSCOUT_DB_SITE = "https://amzscout.net/app/#/database"


@deprecated
def search_and_write_amzscout(
    driver: WebDriver,
    csv_writer: Writer,
    query: str,
    proxy: str | None = None,
    *,
    write_headers: bool = True,
    write_data: bool = True,
) -> None:
    """
    Search for a query and write the results to a CSV file.

    Args:
        driver:
        csv_writer:
        proxy:
        query:
        write_headers:
        write_data:

    Returns:

    """
    wait = WebDriverWait(driver, driver.timeouts.implicit_wait)

    logger.info(f"Searching for {query!r}...")

    if driver.current_url != AMZSCOUT_DB_SITE:
        driver.get(AMZSCOUT_DB_SITE)
    else:
        driver.refresh()  # don't waste time

    # TODO: Filters go here

    # enter prompt
    (driver.find_element(By.ID, "keywords").find_element(By.TAG_NAME, "input").send_keys(query))

    # click "FIND PRODUCTS"
    wait.until(
        ec.element_to_be_clickable((By.CSS_SELECTOR, "button.db-filters__controlls-find-btn"))
    ).click()
    if distraction := ec.element_to_be_clickable(
        (By.CSS_SELECTOR, "app-filter-attention button.btn")
    )(driver):
        distraction.click()  # close the "attention" popup
        wait.until(
            ec.element_to_be_clickable((By.CSS_SELECTOR, "button.db-filters__controlls-find-btn"))
        ).click()
        # run it back

    # wait for results to load
    wait.until(ec.visibility_of_element_located((By.CSS_SELECTOR, "div.loader__text")))
    wait.until(ec.invisibility_of_element_located((By.CSS_SELECTOR, "div.loader__text")))

    if write_headers:
        # TODO: Write headers here
        pass

    if write_data:
        if driver.find_element(By.CSS_SELECTOR, "div.empty-row").is_displayed():
            logger.warning(f"No results found for query {query!r}, skipping...")
        else:
            # TODO: Write data here
            pass

    raise NotImplementedError(
        "I didn't get this far, sorry! Please use the extension mode for now."
    )
    # for a couple different reasons, doing this without the extension is a pretty dumb idea.
    # #1: the rate limit for the dedicated website is a lot lower (more accounts = more IPs)
    # #2: amazon loading is not the rate limit of the project
    # #3: less products on dedicated website
    # its for all these reasons i wont continue developing the dedicated website scraper.


__all__ = ("search_and_write_amzscout", "search_and_write_amazon")
