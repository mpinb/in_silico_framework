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
import re


def read(file):
    """
    The function below can read the transformation matrix numbers written
    in an am file

    """
    matrix = []
    vector = []
    row = []
    with open(file, 'r') as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            if line.rfind("TransformationMatrix") > -1:
                matches = re.findall('-?\d+\.\d+|-?\d+', line)
                vector = list(map(float, matches))
        for i in range(4):
            for j in range(4):
                k = j + i * 4
                row.append(vector[k])
            matrix.append(row)
            row = []

    return matrix


def getTransformation(src, dst):
    """
    This function will calculate the affien transformation matrix from
    8 points (4 source poitns and 4 destination points)

    """
    x = np.transpose(np.matrix([src[0], src[1], src[2], src[3]]))
    y = np.transpose(np.matrix([dst[0], dst[1], dst[2], dst[3]]))

    # add ones on the bottom of x and y
    x = np.matrix(np.vstack((x, [1.0, 1.0, 1.0, 1.0])))
    y = np.matrix(np.vstack((y, [1.0, 1.0, 1.0, 1.0])))
    # solve for A2

    trMatrix = y * x.I
    print(trMatrix)
    return trMatrix


def applyTransformationMatrix(points, matrix):
    """
    transforms the first 3 coordinates of the points. 
    """
    trAmPoints4D = []
    for point4D in points:
        point = point4D[:3]
        mPoint = np.matrix(point)
        mTrPoint = mPoint.T
        p = matrix * np.matrix(np.vstack((mTrPoint, 1.0)))
        p = np.array(p.T)
        p_listed = p.tolist()[0]
        # raw_input("somet")
        trAmPoints4D.append(p_listed[0:3] + point4D[3:])

    return trAmPoints4D
