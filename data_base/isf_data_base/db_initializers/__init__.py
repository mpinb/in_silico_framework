"""Initialize a database from raw simulation data.

This package provides modules for initializing databases from simulation results.

:py:mod:`~data_base.isf_data_base.db_initializers.load_simrun_general` provides a general
way to parse raw simulation output to intermediate pickle files, or permanent dask and pandas dataframes.
A database that has been initialized with this module is herafter called a "simrun-initialized" database.

Each other submodule provides an ``init`` method, which builds on top of the previously simrun-initialized data.
"""
