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
