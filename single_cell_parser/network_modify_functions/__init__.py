'''
Created on Feb 16, 2019

@author: abast

This package is contains  functions, that modify the cell and / or network after
both have been initalized.

Such a function can for example be used to deactivate specific synapses at a somadistance. '''

import logging
import importlib

logger = logging.getLogger("ISF").getChild(__name__)


def get(funname):
    module = importlib.import_module(__name__ + '.' + funname)
    fun = getattr(module, funname)
    return fun
