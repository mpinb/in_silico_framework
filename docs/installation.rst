.. _installation:

Installation
============

ISF is available for Linux, macOS and Windows.

For installation and environment management, ISF uses `pixi <https://pixi.sh/latest/>`_. 
Please follow the installation instructions on the `pixi documentation <https://pixi.sh/latest/#installation>`_ 

To install ISF with ``pixi``, simply:

.. code-block:: bash

   git clone https://github.com/mpinb/in_silico_framework.git --depth 1 &&
   cd in_silico_framework &&
   pixi run setup


.. important::
   :title: Windows
   :collapsible:

   Windows support is still experimental.
   If you are using ISF with Dask parallellization on Windows, please monitor your dask dashboard closely.
   In case you encounter any issues, feel free to `open an issue <https://github.com/mpinb/in_silico_framework/issues>`_ and include relevant logs.
   Note that many of the core ISF workflows (network mapping, neuron model generation etc.) require extensive resources, which often implies a (Linux-based) High Performance Computing environment.


Configuration
-------------

ISF works best with a dask server for parallel computing. We provide default scripts to launch a dask server and workers
that should work on most systems. 

.. code-block:: bash

   pixi run launch_dask_server

.. code-block:: bash

   pixi run launch_dask_workers

For High-Performance Computing (HPC), you may want to launch the dask server with custom configuration instead of these default scripts.
The underlying commands for these shortcuts are configured in the ``pyproject.toml`` file.

Usage
-----

We recommend to use ISF within a JupyterLab server for interactive use:

.. code-block:: bash

   pixi run launch_jupyter_lab_server

``pixi`` also supports a ``conda``-style shell activation:

.. code-block:: bash

   pixi shell

This can be useful for executing shell scripts within the ISF environment, or configuring HPC job submissions.
To get started with ISF, feel free to consult the :ref:`tutorials`.

Test ISF
--------

To test if all components of ISF are working as intended, you can run the test suite locally.

.. code-block:: bash

   pixi run test




