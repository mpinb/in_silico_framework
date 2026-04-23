.. _installation:

Installation
============

.. md-tab-set::

   .. md-tab-item:: Linux

      Before installing ISF, make sure you have the following requirements installed:

      .. csv-table::
         :header: "Requirement", "Download", ""

         `pixi <https://pixi.sh/latest/>`_,  `Download <https://pixi.sh/latest/#installation>`__ 
         `git <https://git-scm.com/>`_,   `Download <https://git-scm.com/downloads/linux>`__, Likely already installed

      .. success::
         :title: Check requirements
         :collapsible:

         You can check if the requirements are installed correctly by running the following commands in your terminal:

         .. code-block:: bash

            which pixi
            which git

         Each command should return a path to the program.
         If it doesn't, you may need to restart your shell, or something went wrong during the installation of the requirements.

      You can then install ISF:

      .. code-block:: bash

         git clone https://github.com/mpinb/in_silico_framework.git
         cd in_silico_framework
         pixi run install

   .. md-tab-item:: macOS

      Before installing ISF, make sure you have the following requirements installed:

      .. csv-table::
         :header: "Requirement", "Download"

         `pixi <https://pixi.sh/latest/>`_,  `Download <https://pixi.sh/latest/#installation>`__
         `git <https://git-scm.com/>`_,   `Download <https://git-scm.com/downloads/mac>`__


      .. success::
         :title: Check requirements
         :collapsible:

         You can check if the requirements are installed correctly by running the following commands in your terminal:

         .. code-block:: bash

            which pixi
            which git

         Each command should return a path to the program.
         If it doesn't, you may need to restart your shell, or something went wrong during the installation of the requirements.


      You can then install ISF:

      .. code-block:: bash

         git clone https://github.com/mpinb/in_silico_framework.git
         cd in_silico_framework
         pixi run install

   .. md-tab-item:: Windows

      .. important::

         Windows support is still experimental.
         If you are using ISF with Dask parallellization on Windows, please monitor your dask dashboard closely.
         In case you encounter any issues, feel free to `open an issue <https://github.com/mpinb/in_silico_framework/issues>`_ and include relevant logs.
         Note that many of the core ISF workflows (network mapping, neuron model generation etc.) require extensive resources, which often implies a (Linux-based) High Performance Computing environment.

      Before installing ISF, make sure you have the following requirements installed:

      .. csv-table::
         :header: "Requirement", "Download", ""

         `pixi <https://pixi.sh/latest/>`_,  `Download <https://pixi.sh/latest/#installation>`__
         `git <https://git-scm.com/>`_,   `Download <https://git-scm.com/downloads/win>`__
         `NEURON <https://www.neuron.yale.edu/neuron/>`_ ,  `Download <https://nrn.readthedocs.io/en/latest/install/install_instructions.html#windows>`__, 7.8 ≤ version ≤ 8.2


      .. success::
         :title: Check requirements
         :collapsible:

         You can check if the requirements are installed correctly by running the following commands in your terminal:

         .. code-block:: bash

            which pixi
            which git
            which neuron

         Each command should return a path to the program.
         If it doesn't, you may need to restart your shell, or something went wrong during the installation of the requirements.


      You can then install ISF:

      .. code-block:: bash

         git clone https://github.com/mpinb/in_silico_framework.git
         cd in_silico_framework
         pixi run install

The ISF environment
-------------------
ISF provides two environments:

- ``default``: the runtime environment used when you activate the ISF environment. This includes all dependencies of ISF necessary for normal operation
- ``docs``: dependencies needed to build the ISF documentation

Each ISF environment adapts the following environment variables:

.. md-tab-set::

   .. md-tab-item:: Linux

      - ``PYTHONPATH``: ISF packages are prepended to the ``PYTHONPATH``. In addition, the ``PYTHONPATH`` that existed before activating the ISF environment is preserved within ISF. 
        This allows the user to use ISF in conjunction with other projects, provided that package names and dependencies do not clash.
      - ``ISF_HOME``: the root directory of the ISF project, as installed on the user system.

   .. md-tab-item:: macOS

      - ``PYTHONPATH``: ISF packages are prepended to the ``PYTHONPATH``. In addition, the ``PYTHONPATH`` that existed before activating the ISF environment is preserved within ISF. 
        This allows the user to use ISF in conjunction with other projects, provided that package names and dependencies do not clash.
      - ``ISF_HOME``: the root directory of the ISF project, as installed on the user system.

   .. md-tab-item:: Windows

      - ``PYTHONPATH``: ISF packages and the python packages that ship with your NEURON installation are prepended to the ``PYTHONPATH`` in that order. 
        The NEURON python packages can be found at ``%NEURONHOME%/lib/python``.
        In addition, the ``PYTHONPATH`` that existed before activating the ISF environment is preserved within ISF. 
        This allows the user to use ISF in conjunction with other projects, provided that package names and dependencies do not clash.
      - ``PATH``: The location of your NEURON executables is appended to your ``PATH``, so that you can invoke them from within the environment. These are located at ``%NEURONHOME%/bin``
      - ``ISF_HOME``: the root directory of the ISF project, as installed on the user system.

.. attention::
   The ISF ``pixi`` environment is, similar to other virtual environments, not isolated from system-level or user-level site-packages by default. 
   If you have installed site-packages on the system- or user-level (i.e. not in a virtual environment) you may contaminate your virtual environments in unintended ways.
   It is recommended to install all python packages for any project in a dedicated environment for each project.
   If you encounter unexpected package versions or mismatches, try inspecting the result of:
   
   .. code-block:: bash

      python -c "import site; print(site.getsitepackages())"

   If this returns anything, then you have site packages installed system-wide, and these will interfere with the packages of any virtual environment that uses the same python version.

   .. seealso::
      https://docs.python.org/3/library/site.html


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



.. container:: doc-feedback

   Documentation unclear, incomplete, broken or wrong? `Let us know <https://github.com/mpinb/in_silico_framework/issues/new?template=documentation.md&labels=docs>`_