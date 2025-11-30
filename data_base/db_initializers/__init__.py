# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Initialize a database from raw simulation data.

This package provides modules for initializing databases from simulation results.

:py:mod:`~data_base.db_initializers.load_simrun_general` provides a general
way to parse raw simulation output to intermediate pickle files, or permanent dask and pandas dataframes.
A database that has been initialized with this module is herafter called a "simrun-initialized" database.

Each other submodule provides an ``init`` method, which builds on top of raw simrun data.
"""
