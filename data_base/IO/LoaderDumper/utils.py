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
"""
Convenience methods for data IO.
"""

import six
import numpy as np
import logging
logger = logging.getLogger("ISF").getChild(__name__)

def get_numpy_dtype_as_str(obj):
    """Get a string representation of the numpy dtype of an object.
    
    If the object is of type string, simply return 'str'.

    Python 2 has two types of strings: str and unicode. 
    If left unspecified, numpy will default to unicode of unknown length, which is set to 0.
    Reading this back in results in the loss of string-type column names. 
    For this reason, we construct our own string representation of the numpy dtype of these columns.
    
    Args:
        obj: The object to get the numpy dtype of.
        
    Returns:
        str: The numpy dtype of the object.
    """
    if (isinstance(obj, six.text_type) or isinstance(obj, str)):  # Check if obj is a string
        if six.PY2:
            return '|S{}'.format(len(obj))
        else:
            return '<U{}'.format(len(obj))
    else:
        return str(np.dtype(type(obj)))
