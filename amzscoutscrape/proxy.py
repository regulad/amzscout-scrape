"""
Proxy-juggling code for amzscout-scrape.

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
import random
from concurrent.futures import ThreadPoolExecutor
from copy import copy
from functools import partial
from threading import Event
from typing import Sequence, cast

import requests
from requests import Session

_CACHE: Sequence[dict] | None = None
_USED = set()
logger = logging.getLogger(__package__)


def _fetch_proxies() -> Sequence[dict]:
    global _CACHE
    logger.info("Fetching proxies from proxylist.geonode.com...")
    with requests.get(
        "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&country=US",
        timeout=60,
    ) as r:
        _CACHE = r.json()["data"]
    logger.info(f"Fetched {len(_CACHE)} proxies.")
    return cast(Sequence[dict], _CACHE)


def fetch_working_proxy() -> str:
    """
    Get a random SOCKS5 proxy from proxylist.geonode.com.
    Returns: A SOCKS5 proxy.

    """
    global _CACHE, _USED

    proxy_found = Event()
    good_proxy: str | None = None

    with ThreadPoolExecutor(
        thread_name_prefix="ProxySearch", max_workers=64
    ) as executor, Session() as session:

        def _try_proxy(proxy_with_protocol: str) -> bool:
            nonlocal good_proxy

            logger.debug(f"Trying proxy {proxy_with_protocol}...")

            try:
                with session.get(
                    "https://api.ipify.org",
                    timeout=30,
                    proxies={"http": proxy_with_protocol, "https": proxy_with_protocol},
                ) as r:
                    if not proxy_found.is_set() and r.ok:
                        proxy_found.set()  # no need for a lock?
                        good_proxy = proxy_with_protocol
                        return True
                    else:
                        return False
            except (
                requests.exceptions.ProxyError,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError,
            ) as e:
                return False

        for proxy in _CACHE or _fetch_proxies():
            if proxy["_id"] not in _USED:
                _USED.add(proxy["_id"])
            else:
                continue

            host = proxy["ip"]
            port = proxy["port"]
            for protocol in proxy["protocols"]:
                executor.submit(partial(_try_proxy, f"{protocol}://{host}:{port}"))

        proxy_found.wait()
        executor.shutdown(wait=False, cancel_futures=True)
        logger.info(f"Proxy {good_proxy} succeeded, using...")
        return good_proxy


__all__ = ["fetch_working_proxy"]
