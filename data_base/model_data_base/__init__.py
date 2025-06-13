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
"""
Database system version 1, used by the Oberlaender lab in Bonn.

This has been deprecated in favor of the new database system :py:mod:`data_base.isf_data_base` to keep up to date with
compression formats, and a switch to JSON instead of pickle for metadata and Loader-dumpers.

:skip-doc:
"""

from .model_data_base import ModelDataBase