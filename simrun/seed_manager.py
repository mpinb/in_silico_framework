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

    if os.name == "nt":
        # Poor windows is limited to int32 :(
        seed = np.random.randint(0, 1_000_000)
    else:
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
