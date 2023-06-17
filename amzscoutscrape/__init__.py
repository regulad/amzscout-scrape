"""
Metadata for this amzscout-scrape.

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
from importlib.metadata import PackageNotFoundError
from importlib.metadata import metadata as __load
from pathlib import Path
from typing import Sequence

pkg = Path(__file__).absolute().parent.name
logger = logging.getLogger(pkg)
metadata = None
try:
    metadata = __load(pkg)
    __status__ = "Development"
    __copyright__ = "Copyright 2023"
    __date__ = "2023-06-16"
    __uri__ = metadata["home-page"]
    __title__ = metadata["name"]
    __summary__ = metadata["summary"]
    __license__ = metadata["license"]
    __version__ = metadata["version"]
    __author__ = metadata["author"]
    __maintainer__ = metadata["maintainer"]
    __contact__ = metadata["maintainer"]
except PackageNotFoundError:  # pragma: no cover
    logger.error(f"Could not load package metadata for {pkg}. Is it installed?")


class AmzscoutscrapeAssets:
    """
    Utilities and resources for ${Project}.
    """

    @classmethod
    def path(cls, *nodes: Sequence[str]) -> Path:
        """
        Gets the ``Path`` of an asset under ``resources``.

        Args:
            nodes: Path nodes underneath ``resources``

        Returns:
            The final ``Path``

        Raises:
            FileNotFoundError: If the path does not exist
        """
        path = Path(Path(__file__).parent, "resources", *nodes)
        if not path.exists():
            raise FileNotFoundError(f"Asset {path} not found")
        return path


if __name__ == "__main__":  # pragma: no cover
    if metadata is not None:
        print(f"{pkg} (v{metadata['version']})")
    else:
        print(f"Unknown project info for {pkg}")
