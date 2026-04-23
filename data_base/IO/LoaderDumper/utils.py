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
