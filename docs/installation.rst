Installation
============

ISF is available for Linux and OSX. It requires ``gcc`` and ``git`` to be installed.

For installation and environment management, ISF uses [`pixi`](https://pixi.sh/latest/). To install ISF with `pixi`, simply:

.. code-block:: bash

   git clone https://github.com/mpinb/in_silico_framework.git && cd in_silico_framework
   pixi install

The installation will:
1. Download a Python 3.8 distribution
2. Download and install conda dependencies
3. Download and install PyPI dependencies
4. Install and patch [`pandas-msgpack`](https://github.com/abast/pandas-msgpack)
5. Install a corresponding ipykernel for notebooks
6. Compile all mechanisms in the ``mechanisms`` directory using ``nrnivmodl``.