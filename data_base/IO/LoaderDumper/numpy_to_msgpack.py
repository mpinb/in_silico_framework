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
"""Read and write numpy arrays to msgpack files
"""


import os
# import cloudpickle
import compatibility
import pandas as pd
import numpy as np
from . import parent_classes
import isf_pandas_msgpack
import json


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(obj, np)  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        return isf_pandas_msgpack.read_msgpack(
            os.path.join(savedir, 'pandas_to_msgpack')).values


def dump(obj, savedir):
    obj = pd.DataFrame(obj)
    #     obj.to_msgpack(os.path.join(savedir, 'pandas_to_msgpack'), compress = 'blosc')
    isf_pandas_msgpack.to_msgpack(os.path.join(savedir, 'pandas_to_msgpack'),
                              obj,
                              compress='blosc')

    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)
