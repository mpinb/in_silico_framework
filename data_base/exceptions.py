""":py:mod:`data_base` specific exceptions.
"""
import warnings

class DataBaseException(Exception):
    '''Typical data_base errors'''
    pass

class ModelDataBaseException(Exception):
    '''Typical model_data_base errors
    
    :skip-doc:'''
    pass

class ISFDataBaseException(Exception):
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