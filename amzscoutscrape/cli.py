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

import logging
import time

import typer

from amzscoutscrape import __copyright__, __title__, __version__, metadata

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


if __name__ == "__main__":
    cli()
