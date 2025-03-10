.. _installation:

Installation
============

ISF is available for Linux and macOS.

For installation and environment management, ISF uses `pixi <https://pixi.sh/latest/>`_. 
You can install ``pixi`` by running:

.. code-block:: bash

   curl -fsSL https://pixi.sh/latest | bash

To install ISF with ``pixi``, simply:

.. code-block:: bash

   git clone https://github.com/mpinb/in_silico_framework.git --depth 1 &&
   cd in_silico_framework &&
   pixi install

Usage
-----

ISF works best with a dask server for parallel computing:

.. code-block:: bash

   pixi run launch_dask_server

.. code-block:: bash

   pixi run launch_dask_workers

We recommend to use ISF within a JupyterLab server for interactive use:

.. code-block:: bash

   pixi run launch_jupyter_lab_server

To get started with ISF, feel free to consult the :ref:`tutorials`.

Configuration
-------------

The scripts above have been configured for local use. For High Performance Computing (HPC) environments, you may
want to adapt these to you own needs. The underlying commands for these shortcuts are 
configured in the ``pyproject.toml`` file.

``pixi`` also supports a ``conda``-style shell activation:

.. code-block:: bash

   pixi shell

This can be useful for executing shell scripts within the ISF environment, configuring HPC job submissions, or simply interactive
IPython sessions.