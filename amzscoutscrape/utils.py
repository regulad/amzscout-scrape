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
from typing import Mapping, TypeVar

K = TypeVar("K")
V = TypeVar("V")


def reverse_map(dictionary: Mapping[K, V], value: V) -> K | None:
    for k, v in dictionary.items():
        if v == value:
            return k


__all__ = ("reverse_map",)
