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
""":skip-doc:"""

import numpy as np


def max_array_dimensions(*args):
    '''takes numpy arrays and returnes the maximal dimensions'''
    for x in args:
        if not isinstance(x, np.ndarray):
            raise RuntimeError("wrong input type. Expect numpy.array, got %s" %
                               str(type(x)))

    #ignore empty arrays
    args = [a for a in args if len(a.shape) == 2]
    list_size = list(map(np.shape, args))
    list_size = list(zip(*list_size))
    list_size = list(map(max, list_size))
    return list_size


def add_aligned(*args):
    '''takes numpy arrays, which may have different sizes and adds them in the following way:
    All arrays are aligned to the top left corner. Then they are expanded, until they are
    as big as the biggest array. Then they are added.'''
    maxSize = max_array_dimensions(*args)  #includes typechecking
    out = np.zeros(maxSize)
    for x in args:
        #ignore empty arrays
        if not len(x.shape) == 2:
            continue
        y = x.copy()
        y = np.concatenate((y, np.zeros([maxSize[0] - y.shape[0], y.shape[1]])),
                           axis=0)
        y = np.concatenate((y, np.zeros([y.shape[0], maxSize[1] - y.shape[1]])),
                           axis=1)
        out = out + y

    return out
