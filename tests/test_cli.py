"""
Tests for command-line interface.

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
import contextlib
import io

import pytest

from amzscoutscrape import cli

from . import TestResources


class TestCli:
    def test_cli(self):
        with TestResources.capture() as capture:
            response = cli.info()
        assert f"Processed 100 things." in capture.stdout
        assert capture.stderr.strip() == ""


if __name__ == "__main__":
    pytest.main()
