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
"""Read and write data.

This subpackage provides mainly the :py:mod:`~data_base.isf_data_base.IO.LoaderDumper` subpackage to read and write data
in various file formats and data types.

In additions, it provides some convenience methods for dask.
"""

import logging
import sys
sys.modules['isf_data_base.IO'] = sys.modules[__name__]

logger = logging.getLogger("ISF").getChild(__name__)