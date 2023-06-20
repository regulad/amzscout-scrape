"""
Command-line interface for amzscout-scrape.

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

from __future__ import annotations

import csv
import logging
import os
import time
from pathlib import Path
from typing import Optional, cast

import typer
from _csv import Writer
from rich.logging import RichHandler
from rich.progress import track
from selenium.webdriver.remote.webdriver import WebDriver

from . import AmzscoutscrapeAssets, __copyright__, __title__, __version__, metadata
from .driver import Driver, create_fresh_driver
from .scrape import search_and_write_amazon, search_and_write_amzscout

logger = logging.getLogger(__package__)
cli = typer.Typer()

USES_OF_EXTENSION = 15
USES_OF_DEDICATED = 5


def info(n_seconds: float = 0.01, verbose: bool = False) -> None:
    """
    Get info about amzscout-scrape.

    Args:
        n_seconds: Number of seconds to wait between processing.
        verbose: Output more info

    Example:
        To call this, run: ::

            from testme import info
            info(0.02)
    """
    typer.echo(f"{__title__} version {__version__}, {__copyright__}")
    if verbose:
        typer.echo(str(metadata.__dict__))
    total = 0
    with typer.progressbar(range(100)) as progress:
        for value in progress:
            time.sleep(n_seconds)
            total += 1
    typer.echo(f"Processed {total} things.")


@cli.command()
def generate(
    filename: str = "amzscout.csv",
    verbosity: int = 0,
    headful: bool = False,
    driver_type: str = "default",
    queries: int = -1,
    skip: int = 0,
    timeout: Optional[float] = None,
    proxy: Optional[str] = None,
    extension: bool = True,
) -> None:
    """
    Generate a basic csv from AMZScout data.
    Returns:


    Args:
        skip: How many queries to skip ahead
        verbosity: How verbose the program should be. 0 is default (errors), 1 is warnings, 2 is info, 3 is debug.
        queries: The number of queries to run. Defaults to None, which means all queries.
        filename: The filename to write to. Defaults to "amzscout.csv".
        headful: Weather or not a Chrome window should be opened. This is only useful for debugging.
        driver_type: The driver to use. Defaults to "default", which is the best match for your OS. Options include "chrome", "edge", "firefox", and "undetected".
        timeout: The number of seconds to wait for the page to load before giving up.
        proxy: A proxy to use. If left unspecified, the system proxy will be utilized. If set to "direct://" no proxy will be used.
        extension: Use the legacy scraper. This is slower, but more reliable.
    """
    log_level = logging.ERROR
    match verbosity:
        case 0:
            log_level = logging.ERROR
        case 1:
            log_level = logging.WARNING
        case 2:
            log_level = logging.INFO
        case 3:
            log_level = logging.DEBUG

    logging.basicConfig(level=log_level, handlers=[RichHandler()])

    driver_enum_value: Driver = Driver.U_CHROME
    match driver_type:
        case "default":
            if extension:
                driver_enum_value = (
                    Driver.U_CHROME
                )  # safety on Amazon.com they have a lot of bot detection
            else:
                if os.name == "nt":
                    # Windows users already have Edge installed, so we'll use that.
                    driver_enum_value = Driver.EDGE
                else:
                    # Linux and macOS users probably want Firefox.
                    driver_enum_value = Driver.FIREFOX
        case "chrome":
            driver_enum_value = Driver.CHROME
        case "edge":
            driver_enum_value = Driver.EDGE
        case "firefox":
            driver_enum_value = Driver.FIREFOX
        case "undetected":
            driver_enum_value = Driver.U_CHROME
        case _:
            logger.warning(f"Invalid driver {driver_type!r}")

    with AmzscoutscrapeAssets.path("amazon_products.txt").open("r", encoding="utf-8") as fp:
        potential_queries = [line.strip() for line in fp.readlines()][skip:queries]

    filepath = Path(filename).absolute()

    exists = filepath.exists()
    with filepath.open("w" if not exists else "a", newline="", encoding="utf-8") as fp:
        csv_writer = cast(Writer, csv.writer(fp, dialect="excel"))

        typer.echo(f"Writing to {filepath.absolute()}")

        driver: WebDriver | None = None

        try:
            fails = 0
            for i, query in track(
                enumerate(potential_queries),
                description="Scraping (this WILL take a while)...",
                total=len(potential_queries),
            ):
                # Every 14 queries, restart the browser to avoid getting blocked out.
                use_count = USES_OF_DEDICATED if not extension else USES_OF_EXTENSION
                if i % use_count == 0 and driver is not None:
                    logger.info("Driver expired, killing...")
                    driver.quit()
                    driver = None
                while driver is None:
                    logger.info("Attempting to create a new driver...")
                    driver = create_fresh_driver(
                        headless=not headful,
                        timeout=timeout,
                        driver_type=driver_enum_value,
                        proxy=proxy,
                        load_extension=extension,
                    )
                try:
                    logger.info(f"Starting {query!r}, #{i + skip}...")
                    if extension:
                        search_and_write_amazon(
                            driver,
                            csv_writer,
                            query,
                            write_headers=i == 0 and not exists,
                            proxy=proxy,
                        )
                    else:
                        search_and_write_amzscout(
                            driver,
                            csv_writer,
                            query,
                            write_headers=i == 0 and not exists,
                            proxy=proxy,
                        )
                except Exception as e:
                    fails += 1
                    logger.exception(f"Error while processing query {query!r}: {e}")
                    logger.info(f"Skipping {query!r}, {fails} fails so far...")
            logger.info(
                f"Completed lookup of {len(potential_queries)} queries." f" {fails} failed."
            )
            logger.info(f"Fail rate: {fails / len(potential_queries) * 100:.2f}%")
        finally:
            if driver is not None:
                logger.info("Closing driver...")
                driver.quit()

        typer.echo("Done! Enjoy your freshly-picked data!")


if __name__ == "__main__":
    cli()
