# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.
"""Initialize a database from raw simulation data.

This package provides modules for initializing databases from simulation results.

:py:mod:`~data_base.db_initializers.load_simrun_general` provides a general
way to parse raw simulation output to intermediate pickle files, or permanent dask and pandas dataframes.
A database that has been initialized with this module is herafter called a "simrun-initialized" database.

Each other submodule provides an ``init`` method, which builds on top of the previously simrun-initialized data.
"""
