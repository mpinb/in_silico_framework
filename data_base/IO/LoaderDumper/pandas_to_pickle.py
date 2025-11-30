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
"""Read and write a pandas DataFrame to the pickle format.

See also:
    :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.pandas_to_parquet` for the Apache parquet format.
"""


import os
# import cloudpickle
import compatibility
import pandas as pd
from . import parent_classes
import json


def check(obj):
    """Check whether the object can be saved with this dumper
    
    Args:
        obj (object): Object to be saved
        
    Returns:
        bool: Whether the object is a pandas DataFrame or Series.
    """
    return isinstance(
        obj, (pd.DataFrame,
              pd.Series))  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):
    """Loader for pickle files to pandas DataFrames"""
    def get(self, savedir):
        """Load the pandas DataFrame from the specified folder
        """
        return pd.read_pickle(os.path.join(savedir, 'pandas_to_pickle.pickle'))


def dump(obj, savedir):
    """Save the pandas DataFrame to a ``.pickle`` file in the specified directory
    
    Args:
        obj (pd.DataFrame): Pandas DataFrame to be saved.
        savedir (str): Directory where the pandas DataFrame should be stored.
    """
    obj.to_pickle(os.path.join(savedir, 'pandas_to_pickle.pickle'))

    with open(os.path.join(savedir, 'Loader.json'), 'w') as f:
        json.dump({'Loader': __name__}, f)
