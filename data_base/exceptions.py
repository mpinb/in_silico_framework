"""
This module provides a collection of data_base specific exceptions

The main reason that these are in a separate module is to avoid circular imports:
1. data_base import isf_data_base to register isf_data_base.IO under the name data_base.IO
2. data_base.isf_data_base imports data_base.data_base_register, as this register should not care whether or not it is model_data_base, data_base or isf_data_base
3. data_base.data_base_register imports DataBaseExceptions. If these are defined in any of the modules named above, we have circular imports.
"""
import warnings

class DataBaseException(Exception):
    '''Typical data_base errors'''
    pass

class ModelDataBaseException(Exception):
    '''Typical model_data_base errors'''
    pass

class ISFDataBaseException(Exception):
    '''Typical isf_data_base errors'''
    pass


class DataBaseWarning(Warning):
    def __init__(self, message):
        self.message = message
        
    def __str__(self):
        return repr(self.message)