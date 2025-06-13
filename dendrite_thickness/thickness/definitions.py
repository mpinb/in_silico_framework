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

import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT_DIR, 'configuration.conf')
"""Definitions of Data structures:
        1. coordinate_2d, TYPE: 2d list of floats
        2. image_coordinate_2d, TYPE: 2d list of floats, in a relative unit such that 1 reflects the pixel size:
        3. coordinate, TYPE: 3d list of floats
        4. pixel_coordinate, TYPE: 2d list of integers
        5. indices: 2d pixel position in an image, list of 2 integers.
        6. src_points,
        7. dst_points,
"""