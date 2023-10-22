<div align="center">

<img src="./docs/_static/_figures/triple_spike.gif" alt="L5PT triple burst">

# The In-Silico-Framework (ISF)
[![In-Silico-Framework (Python 2.7) install and test](https://github.com/research-center-caesar/in_silico_framework/actions/workflows/test-isf-py27-local.yml/badge.svg)](https://github.com/research-center-caesar/in_silico_framework/actions/workflows/test-isf-py27-local.yml)
[![In-Silico-Framework (Python 3.8) install and test](https://github.com/research-center-caesar/in_silico_framework/actions/workflows/test-isf-py38-local.yml/badge.svg)](https://github.com/research-center-caesar/in_silico_framework/actions/workflows/test-isf-py38-local.yml)
[![In-Silico-Framework (Python 3.9) install and test](https://github.com/research-center-caesar/in_silico_framework/actions/workflows/test-isf-py39-local.yml/badge.svg)](https://github.com/research-center-caesar/in_silico_framework/actions/workflows/test-isf-py39-local.yml)
[![codecov](https://codecov.io/gh/mpinb/in_silico_framework/graph/badge.svg?token=V4P4QMFM12)](https://codecov.io/gh/mpinb/in_silico_framework)
</div>

## Installation

Every student needs to be able to synchronize their repository with https://github.com/research-center-caesar/in_silico_framework. Detailed instructions on how to install the repo are given in the [installer directory](./installer/).

## Documentation

The current state of the documentation is currently [locally hosted on ibs3005](http://10.40.130.27:8000/) (only accessible via somalogin01/02).

Documentation is a work in progress. It is generated automatically from docstrings using Sphinx autosummary. Missing entries in the documentation are generally due to missing docstrings in the source code.

## Usage

The [Interface module](./Interface.py) glues together all submodules and gives direct access to them. Rather than importing individual submodules, it is recommended to access them via Interface. Most of your code will probably start with
```python
import Interface as I
```

A walkthrough of the capabilities of ISF is presented in the ["Getting Started" notebook](./getting_started/getting_started.ipynb).