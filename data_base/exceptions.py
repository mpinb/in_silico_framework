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
""":py:mod:`data_base` specific exceptions.
"""

class DataBaseException(Exception):
    '''Typical data_base errors'''
    pass

class ModelDataBaseException(DataBaseException):
    '''Typical model_data_base errors
    
    :skip-doc:'''
    pass

class ISFDataBaseException(DataBaseException):
    '''Typical isf_data_base errors'''
    pass


class DataBaseWarning(Warning):
    """Warnings are usually handled by the logger. However, if you want to raise a warning, you can use this class.
    
    :skip-doc:
    """
    def __init__(self, message):
        self.message = message
        
    def __str__(self):
        return repr(self.message)
