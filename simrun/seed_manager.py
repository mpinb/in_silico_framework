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

"""Get a random seed"""

import numpy as np
#path = '/nas1/Data_arco/used_seeds'
import os

path = os.path.join(os.path.dirname(__file__), 'used_seeds')


def get_seed(recursion_depth=0):
    '''Get a random seed.
    
    Returns:
        int: A random seed.
    '''
    # TODO: the used_seeds functionality should be either extended or removed.  - Bjorge
    used_seeds = []
    try:
        used_seeds = np.fromfile('/home/abast/used_seeds', dtype='int')
        used_seeds = used_seeds.tolist()
    except IOError:
        pass

    used_seeds.extend(list(range(10000)))

    seed = np.random.randint(4294967295)  #Seed must be between 0 and 4294967295
    return seed
    
    if not seed in used_seeds:
        used_seeds.append(seed)
        used_seeds = np.array(used_seeds)
        used_seeds = np.unique(
            used_seeds
        )  #because otherwise, the extend command above will allways add the same seeds
        used_seeds.tofile(path)
        return seed
    elif recursion_depth >= 50:
        raise RuntimeError("Failed generating random seed")
    else:
        return get_seed(recursion_depth=recursion_depth + 1)
