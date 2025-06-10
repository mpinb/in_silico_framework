<div align="center">

<img src=./docs/_static/_images/isf-logo-white.png#gh-dark-mode-only width='350'>
<img src=./docs/_static/_images/isf-logo-black.png#gh-light-mode-only width='350'>

# The In Silico Framework (ISF)

An In Silico Framework for multi-scale modeling and analysis of *in vivo* neuron-network mechanisms

[![Linux](https://img.shields.io/github/actions/workflow/status/mpinb/in_silico_framework/test-isf-py38-pixi-linux.yml?style=flat-square&logo=linux&logoColor=white&label=Linux
)](https://github.com/mpinb/in_silico_framework/actions/workflows/test-isf-py38-pixi-linux.yml)
[![macOS](https://img.shields.io/github/actions/workflow/status/mpinb/in_silico_framework/test-isf-py38-pixi-macos.yml?style=flat-square&logo=apple&label=macOS
)](https://github.com/mpinb/in_silico_framework/actions/workflows/test-isf-py38-pixi-macos.yml)
[![docs](https://img.shields.io/github/actions/workflow/status/mpinb/in_silico_framework/pages/pages-build-deployment?style=flat-square&logo=sphinx&label=docs)](https://mpinb.github.io/in_silico_framework)
[![codecov](https://img.shields.io/codecov/c/github/mpinb/in_silico_framework?logo=codecov&style=flat-square
)](https://codecov.io/gh/mpinb/in_silico_framework)

</div>


## 📖 Documentation
Documentation is available at [mpinb.github.io/in_silico_framework](https://mpinb.github.io/in_silico_framework)

## 📝 Tutorials
Tutorials on ISF's most important workflows are available [online](https://mpinb.github.io/in_silico_framework/rst_assets/tutorials.html), and under [getting_started/tutorials](https://github.com/mpinb/in_silico_framework/blob/master/getting_started/tutorials)

## 🔩 Installation

Installation instructions can be found [here](https://mpinb.github.io/in_silico_framework/rst_assets/installation.html), but are also repeated below.

ISF is available for Linux, Windows and macOS.
For installation and environment management, ISF uses [pixi](https://pixi.sh/latest/). 
You can install pixi on Linux and macOS by running:

```bash
curl -fsSL https://pixi.sh/latest | sh
```
and on Windows:
```pwsh
powershell -ExecutionPolicy ByPass -c "irm -useb https://pixi.sh/install.ps1 | iex"
```

To install ISF with pixi, simply:

```bash
git clone https://github.com/mpinb/in_silico_framework.git --depth 1 &&
cd in_silico_framework &&
pixi install &&
pixi configure
```
