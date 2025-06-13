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

import numpy as np



def addUncertainties(amFilesDict050, amFilesDict025, amFilesDict075):
    """
    input:
    1. amFilsDict050: set of slices conatian points with their radii calculated for the base treshold
    2. amFilesDict025: set of slices conatian of points with their radii calculated for the lower bound treshold
    3. amFilesDict075: set of slices conatian of points with their radii calculated for the upper bound treshold

    """
    points = []
    points025 = []
    points075 = []

    for amFile in amFilesDict050:
        points = amFilesDict050[amFile]
        points025 = amFilesDict025[amFile]
        points075 = amFilesDict075[amFile]
        for idx, point in enumerate(points):
            ucr = points025[idx][3] - points075[idx][3]
            if (points[idx][3] != 0.0):
                rel_ucr = (ucr) / points[idx][3]
            else:
                rel_ucr = 0
            points[idx].append(ucr)
            points[idx].append(rel_ucr)
        amFilesDict050[amFile] = points
        points = []

    return amFilesDict050
