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
"""Read and write objects to the msgpack format.
"""

import os
import msgpack
from . import parent_classes
import json


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return True  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        with open(os.path.join(savedir, 'to_pickle_dump'), 'rb') as file_:
            return msgpack.load(file_)


def dump(obj, savedir):
    with open(os.path.join(savedir, 'to_pickle_dump'), 'wb') as file_:
        msgpack.dump(obj, file_)

    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)