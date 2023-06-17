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
import random
import time
from pathlib import Path
from typing import cast

import typer
from _csv import Writer
from rich.progress import Progress, SpinnerColumn, TextColumn, track
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from undetected_chromedriver import Chrome, ChromeOptions

from . import AmzscoutscrapeAssets, __copyright__, __title__, __version__, metadata
from .driver import get_clean_driver
from .scrape import search_and_write

logger = logging.getLogger(__package__)
cli = typer.Typer()


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
    filename: str = "amzscout.csv", headful: bool = False, queries: int = -1, skip: int = 0
) -> None:
    """
    Generate a basic csv from AMZScout data.
    Returns:


    Args:
        skip: How many queries to skip ahead
        queries: The number of queries to run. Defaults to None, which means all queries.
        filename: The filename to write to. Defaults to "amzscout.csv".
        headful: Weather or not a Chrome window should be opened. This is only useful for debugging.
    """
    with AmzscoutscrapeAssets.path("amazon_products.txt").open("r") as fp:
        potential_queries = [line.strip() for line in fp.readlines()][skip:queries]

    filepath = Path(filename).absolute()

    if filepath.exists():
        typer.echo(f"File {filepath.absolute()} already exists. Aborting.")
        raise typer.Abort()

    with filepath.open("w", newline="") as fp:
        csv_writer = cast(Writer, csv.writer(fp, dialect="excel"))

        typer.echo(f"Writing to {filepath.absolute()}")

        driver: WebDriver | None = None

        try:
            for i, query in track(
                enumerate(potential_queries),
                description="Scraping (this WILL take a while)...",
                total=len(potential_queries),
            ):
                # Every 14 queries, restart the browser to avoid getting blocked out.
                if i % 14 == 0:
                    if driver is not None:
                        driver.quit()
                    driver = None
                if driver is None:
                    driver = get_clean_driver(headless=not headful)
                search_and_write(driver, csv_writer, query, write_headers=i == 0)
        finally:
            if driver is not None:
                driver.quit()

        typer.echo("Done! Enjoy your freshly-picked data!")


if __name__ == "__main__":
    cli()
