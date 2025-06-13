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
# import cloudpickle
import compatibility
import numpy as np
from . import parent_classes


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(obj, np)  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        return np.load(os.path.join(savedir, 'np.npy'))


def dump(obj, savedir):
    np.save(os.path.join(savedir, 'np.npy'), obj)

    #     with open(os.path.join(savedir, 'Loader.pickle'), 'wb') as file_:
    #         cloudpickle.dump(Loader(), file_)
    compatibility.cloudpickle_fun(Loader(),
                                  os.path.join(savedir, 'Loader.pickle'))
