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
import msgpack
from . import parent_classes


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return True  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        with open(os.path.join(savedir, 'to_pickle_dump'), 'rb') as file_:
            return msgpack.load(file_)


def dump(obj, path):
    with open(os.path.join(path, 'to_pickle_dump'), 'wb') as file_:
        msgpack.dump(obj, file_)

    with open(os.path.join(path, 'Loader.pickle'), 'wb') as file_:
        msgpack.dump(Loader(), file_)