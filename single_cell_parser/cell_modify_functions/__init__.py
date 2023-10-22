'''
Created on Feb 16, 2019

@author: abast

This package is contains  functions, that modify the cell after
it is initalized.

Such a function can for example be used to scale the apical dendrite.

These kind of modifying functions have caused a lot of trouble in the past, as it 
has not been specified in the neuron parameterfile. No record of whether a modification
had been applied was saved alongside the simulation data.

Now, the cell parameter file can contain the key "cell_modify_functions" in its
neuron section. The value corresponding to that key is a dictionary. The keys of that 
dictionary can be names to modules in this package. The values corresponding to these keys
are the keyword arguments of the respective cell modify function.

I.e.

{'neuron': {
    'Soma': { ... }
    'Dendrite': { ... }
    'filename': {some hocpath}
    'cell_modify_functions': {
        'scale_apical': {'scale': 2.1}
    }}}
'''

import importlib


def get(funname):
    module = importlib.import_module(__name__ + '.' + funname)
    fun = getattr(module, funname)
    return fun
