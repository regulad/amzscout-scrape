# Amzscout-scrape

[![Version status](https://img.shields.io/pypi/status/amzscout-scrape)](https://pypi.org/project/amzscout-scrape)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python version compatibility](https://img.shields.io/pypi/pyversions/amzscout-scrape)](https://pypi.org/project/amzscout-scrape)
[![Version on Docker Hub](https://img.shields.io/docker/v/regulad/amzscout-scrape?color=green&label=Docker%20Hub)](https://hub.docker.com/repository/docker/regulad/amzscout-scrape)
[![Version on GitHub](https://img.shields.io/github/v/release/regulad/amzscout-scrape?include_prereleases&label=GitHub)](https://github.com/regulad/amzscout-scrape/releases)
[![Version on PyPi](https://img.shields.io/pypi/v/amzscoutscrape)](https://pypi.org/project/amzscoutscrape)
[![Version on Conda-Forge](https://img.shields.io/conda/vn/conda-forge/amzscout-scrape?label=Conda-Forge)](https://anaconda.org/conda-forge/amzscout-scrape)
[![Documentation status](https://readthedocs.org/projects/amzscout-scrape/badge)](https://amzscout-scrape.readthedocs.io/en/stable)
[![Build (GitHub Actions)](https://img.shields.io/github/workflow/status/regulad/amzscout-scrape/Build%20&%20test?label=Build%20&%20test)](https://github.com/regulad/amzscout-scrape/actions)
[![Build (Travis)](https://img.shields.io/travis/regulad/amzscout-scrape?label=Travis)](https://travis-ci.com/regulad/amzscout-scrape)
[![Build (Azure)](https://img.shields.io/azure-devops/build/regulad/<<key>>/<<defid>>?label=Azure)](https://dev.azure.com/regulad/amzscout-scrape/_build?definitionId=1&_a=summary)
[![Build (Scrutinizer)](https://scrutinizer-ci.com/g/regulad/amzscout-scrape/badges/build.png?b=main)](https://scrutinizer-ci.com/g/regulad/amzscout-scrape/build-status/main)
[![Test coverage (coveralls)](https://coveralls.io/repos/github/regulad/amzscout-scrape/badge.svg?branch=main&service=github)](https://coveralls.io/github/regulad/amzscout-scrape?branch=main)
[![Test coverage (codecov)](https://codecov.io/github/regulad/amzscout-scrape/coverage.svg)](https://codecov.io/gh/regulad/amzscout-scrape)
[![Test coverage (Scrutinizer)](https://scrutinizer-ci.com/g/regulad/amzscout-scrape/badges/coverage.png?b=main)](https://scrutinizer-ci.com/g/regulad/amzscout-scrape/?branch=main)
[![Maintainability (Code Climate)](https://api.codeclimate.com/v1/badges/<<apikey>>/maintainability)](https://codeclimate.com/github/regulad/amzscout-scrape/maintainability)
[![CodeFactor](https://www.codefactor.io/repository/github/dmyersturnbull/tyrannosaurus/badge)](https://www.codefactor.io/repository/github/dmyersturnbull/tyrannosaurus)
[![Code Quality (Scrutinizer)](https://scrutinizer-ci.com/g/regulad/amzscout-scrape/badges/quality-score.png?b=main)](https://scrutinizer-ci.com/g/regulad/amzscout-scrape/?branch=main)
[![Created with Tyrannosaurus](https://img.shields.io/badge/Created_with-Tyrannosaurus-0000ff.svg)](https://github.com/dmyersturnbull/tyrannosaurus)

Generate a dataset ready for data science from AMZScout without paying a dime.

And it’s further described in this paragraph.
[See the docs 📚](https://amzscout-scrape.readthedocs.io/en/stable/) for more info.

# About

This uses undetected chromedriver and the [AMZScout extension `njopapoodmifmcogpingplfphojnfeea`](https://chrome.google.com/webstore/detail/amazon-product-finder-amz/njopapoodmifmcogpingplfphojnfeea?utm_source=webapp&utm_medium=amzscout_wa&utm_campaign=topbanner?utm_source=webapp) to extract information from Amazon product pages.

# Using

## Dependencies

### Chrome or Chromium

#### Windows

```bash
winget install --id Google.Chrome
```

#### Ubuntu & Debian

```bash
sudo apt-get install chromium-browser
```

#### MacOS & Other

Download [here](https://www.google.com/chrome/) like anywhere else

### `chromedriver`

Make sure you install `chromedriver` on your system alongside a recent version of Chrome or Chromium.

#### brew (macOS only)

```bash
brew install chromedriver
```

#### Scoop (Windows)

Note: scoop only has chromedriver for win32 platforms. If you're on a 64-bit system, your mileage may vary.

```bash
scoop install chromedriver
```

#### Other platforms

Refer to https://sites.google.com/chromium.org/driver/downloads?authuser=0 for instructions downloading chromedriver on your respective system.

### poetry

With a good version of Python installed, run the following:

```bash
pip install pipx
pipx install poetry
```

If you get a memo about it not being on your path, Google will be your best friend.

## Installation

```bash
git clone https://github.com/regulad/amzscout-scrape.git
cd amzscout-scrape
poetry install
```

## Usage

Usage is about as simple as it gets.

```bash
poetry run amzscout-scrape --help
```

It will keep you updated, although it will take a hot minute.

Once it's done, you'll have a CSV file in the current directory.

## Proxy

Included is a simple Tailscale configuration that serves a SOCKS5 proxy on your local machine.

Copy the contents of `proxy.env-example` into `.env`, populate the fields and then perform the following command on a machine that has docker installed:

```bash
docker-compose up -d
```

Then, you can use the `--proxy` flag to use the proxy.

```bash
poetry run amzscout-scrape --proxy socks5://localhost:1055
```

# Appendix

Licensed under the terms of the [Apache License 2.0](https://spdx.org/licenses/Apache-2.0.html).
[New issues](https://github.com/regulad/amzscout-scrape/issues) and pull requests are welcome.
Please refer to the [contributing guide](https://github.com/regulad/amzscout-scrape/blob/main/CONTRIBUTING.md)
and [security policy](https://github.com/regulad/amzscout-scrape/blob/main/SECURITY.md).
Generated with [Tyrannosaurus](https://github.com/dmyersturnbull/tyrannosaurus).
