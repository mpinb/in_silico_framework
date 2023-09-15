'''
Created on Nov 08, 2018

@author: abast
'''
from __future__ import absolute_import

# from functools import partial
# import numpy as np
# import pandas as pd
# 
# import single_cell_parser as scp
# 
# from . import setup_stim
# from .utils import tVec, vmSoma, vmApical
# from .parameters import set_fixed_params, param_to_kwargs
from .parameters import param_to_kwargs
# from .simulator import Simulator, run_fun
# from .L5tt_parameter_setup import get_L5tt_template, set_morphology, set_ephys, set_hot_zone, set_param, set_many_param
# # moved to bottom to resolve circular import
# # from .hay_evaluation import hay_evaluate_BAC, hay_evaluate_bAP, hay_evaluate_StepOne, hay_evaluate_StepTwo, hay_evaluate_StepThree
# 
from .evaluator import Evaluator
from toolz.dicttoolz import merge
# 
# from .combiner import Combiner


from . import hay_evaluation_python
from .utils import tVec, vmSoma, vmApical, vmMax
import numpy as np



################################################
# Simulator
################################################

def record_bAP(cell, recSite1 = None, recSite2 = None):
    assert(recSite1 is not None)
    assert(recSite2 is not None)
    return {'tVec': tVec(cell), 
            'vList': (vmSoma(cell), vmApical(cell, recSite1), vmApical(cell, recSite2)),
            'vMax': vmMax(cell)}

def record_BAC(cell, recSite = None):
    return {'tVec': tVec(cell), 
            'vList': (vmSoma(cell), vmApical(cell, recSite)),
            'vMax': vmMax(cell)}

def record_Step(cell):
    return {'tVec': tVec(cell), 
            'vList': [vmSoma(cell)],
            'vMax': vmMax(cell)}


def get_Simulator(fixed_params, step = False, vInit = False):
    s = hay_complete_default_setup.get_Simulator(fixed_params, step = step)
    s.setup.stim_response_measure_funs = []
    s.setup.stim_response_measure_funs.append(['bAP.hay_measure', param_to_kwargs(record_bAP)])
    s.setup.stim_response_measure_funs.append(['BAC.hay_measure', param_to_kwargs(record_BAC)])
    if vInit:
        raise NotImplementedError
    return s

######################################################
# Evaluator
######################################################
def interpolate_vt(voltage_trace_):
    out = {}
    for k in voltage_trace_:
        t = voltage_trace_[k]['tVec']
        t_new = np.arange(0, max(t), 0.025)
        vList_new = [np.interp(t_new, t, v) for v in voltage_trace_[k]['vList']] # I.np.interp
        out[k] = {'tVec': t_new, 'vList': vList_new}
        if 'iList' in voltage_trace_[k]:
            iList_new = [np.interp(t_new, t, i) for i in voltage_trace_[k]['iList']]
            out[k] = {'tVec': t_new, 'vList': vList_new, 'iList': iList_new}  
    return out

def map_truefalse_to_str(dict_):
    def _helper(x):
        if (x is True) or (x is np.True_):
            return 'True'
        elif (x is False) or (x is np.False_):
            return 'False'
        else:
            return x
    return {k: _helper(dict_[k]) for k in dict_}
    
def get_Evaluator(step = False, vInit = False, bAP_kwargs = {}, BAC_kwargs = {}, interpolate_voltage_trace = True):
    e = Evaluator()
    bap = hay_evaluation_python.bAP(**bAP_kwargs)
    bac = hay_evaluation_python.BAC(**BAC_kwargs)
    
    if interpolate_voltage_trace:
        e.setup.pre_funs.append(interpolate_vt)
    
    e.setup.evaluate_funs.append(['BAC.hay_measure', 
                                  bac.get,
                                  'BAC.hay_features'])

    e.setup.evaluate_funs.append(['bAP.hay_measure',
                                  bap.get,
                                  'bAP.hay_features'])

    if step:
        raise NotImplementedError
    if vInit:
        raise NotImplementedError
    e.setup.finalize_funs.append(lambda x: merge(list(x.values()))) 
    e.setup.finalize_funs.append(map_truefalse_to_str)    
    
    return e

##############################################################
# Combiner
##############################################################

def get_Combiner(step = False):
    return hay_complete_default_setup.get_Combiner(step = step)

from . import hay_complete_default_setup