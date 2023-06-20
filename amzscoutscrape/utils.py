"""
Utility code for amzscout-scrape.

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
import functools
import logging
import time
import warnings
from typing import Mapping, TypeVar

K = TypeVar("K")
V = TypeVar("V")

logger = logging.getLogger(__package__)


def reverse_map(dictionary: Mapping[K, V], value: V) -> K | None:
    for k, v in dictionary.items():
        if v == value:
            return k


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.simplefilter("always", DeprecationWarning)  # turn off filter
        warnings.warn(
            "Call to deprecated function {}.".format(func.__name__),
            category=DeprecationWarning,
            stacklevel=2,
        )
        warnings.simplefilter("default", DeprecationWarning)  # reset filter
        return func(*args, **kwargs)

    return new_func


# https://keestalkstech.com/2021/03/python-utility-function-retry-with-exponential-backoff/
# with special sauce mods
def retry(tries=5, backoff_seconds=1):
    def rwb(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            attempts = 0
            while True:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    if (
                        type(e) == KeyboardInterrupt
                        or type(e) == SystemExit
                        or type(e) == NotImplementedError
                    ):
                        raise

                    if attempts == tries:
                        raise

                    sleep = backoff_seconds * 2**attempts

                    logger.exception(f"Retrying {f.__name__} in {sleep} seconds due to {e}")

                    time.sleep(sleep)
                    attempts += 1

        return wrapper

    return rwb


# TODO: add timeout context manager
# https://stackoverflow.com/questions/2281850/timeout-function-if-it-takes-too-long-to-finish


__all__ = ("reverse_map", "deprecated", "retry")
