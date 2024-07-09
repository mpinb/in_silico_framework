'''
A Python translation of the setup for in-silico curernt injection experiments as described in :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`.

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


def record_bAP(cell, recSite1=None, recSite2=None):
    """Extract the voltage traces from the soma and two apical dendritic locations.
    
    This is used to quantify the voltage trace of a backpropagating AP (bAP)
    stimulus in a pyramidal neuron. THe two apical recording sites are used
    to calculate e.g. backpropagating attenuation.
    
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell object.
        recSite1 (float): The distance (um) from the soma to the first recording site.
        recSite2 (float): The distance (um) from the soma to the second recording site.
        
    Note:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    assert recSite1 is not None
    assert recSite2 is not None
    return {
        'tVec': tVec(cell),
        'vList': (vmSoma(cell), 
                  vmApical(cell,recSite1), 
                  vmApical(cell, recSite2)),
        'vMax': vmMax(cell)
    }


def record_BAC(cell, recSite=None):
    """Extract the voltage traces from the soma and an apical dendritic location.
    
    This is used to quantify the voltage trace of a bAP-Activated Ca2+ (BAC) stimulus
    
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell object.
        recSite (float): The distance (um) from the soma to the apical recording site.
        
    Note:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    return {
        'tVec': tVec(cell),
        'vList': (vmSoma(cell), vmApical(cell, recSite)),
        'vMax': vmMax(cell)
    }


def record_Step(cell):
    """Extract the voltage trace from the soma.
    
    This is used to quantify the response of the cell to step currents.
    
    Note:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    return {
        'tVec': tVec(cell), 
        'vList': [vmSoma(cell)], 
        'vMax': vmMax(cell)}


def get_Simulator(fixed_params, step=False, vInit=False):
    """Get a set up :class:`~biophysics_fitting.simulator.Simulator` object for the Hay protocol.
    
    Given cell-specific fixed parameters, set up a simulator object for the Hay protocol,
    including measuring functions for bAP and BAC stimuli (no step currents)
    
    Args:
        fixed_params (dict): A dictionary of fixed parameters for the cell.
        step (bool): Whether to include step current measurements.
        vInit (bool): Whether to include vInit measurements. (not implemented yet)
        
    Returns
        (:class:`~biophysics_fitting.simulator.Simulator`): A simulator object.
        
    Note:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.    
    """
    s = hay_complete_default_setup.get_Simulator(fixed_params, step=step)
    s.setup.stim_response_measure_funs = []
    s.setup.stim_response_measure_funs.append(
        ['bAP.hay_measure', param_to_kwargs(record_bAP)])
    s.setup.stim_response_measure_funs.append(
        ['BAC.hay_measure', param_to_kwargs(record_BAC)])
    if vInit:
        raise NotImplementedError
    return s


######################################################
# Evaluator
######################################################
def interpolate_vt(voltage_trace_):
    """Interpolate a voltage trace so that is has fixed time interval
    
    The NEURON simulator allows for a variable time step, which can make
    comparing voltage traces difficult. This function interpolates the voltage
    traces so that they have a fixed time interval of 0.025 ms.
    
    Args:
        voltage_trace_ (dict): A dictionary of voltage traces.
        
    Returns:
        dict: A dictionary of voltage traces with a fixed time interval.
    """
    out = {}
    for k in voltage_trace_:
        t = voltage_trace_[k]['tVec']
        t_new = np.arange(0, max(t), 0.025)
        vList_new = [
            np.interp(t_new, t, v) for v in voltage_trace_[k]['vList']
        ]  # I.np.interp
        out[k] = {'tVec': t_new, 'vList': vList_new}
        if 'iList' in voltage_trace_[k]:
            iList_new = [
                np.interp(t_new, t, i) for i in voltage_trace_[k]['iList']
            ]
            out[k] = {'tVec': t_new, 'vList': vList_new, 'iList': iList_new}
    return out


def map_truefalse_to_str(dict_):
    """Convert True/False to 'True'/'False' in a dictionary
    
    Args:
        dict_ (dict): A dictionary with boolean values.
        
    Returns:
        dict: A dictionary with boolean values converted to strings.
    """
    def _helper(x):
        if (x is True) or (x is np.True_):
            return 'True'
        elif (x is False) or (x is np.False_):
            return 'False'
        else:
            return x

    return {k: _helper(dict_[k]) for k in dict_}


def get_Evaluator(
    step=False,
    vInit=False,
    bAP_kwargs={},
    BAC_kwargs={},
    interpolate_voltage_trace=True
    ):
    """Get a set up :class:`~biophysics_fitting.evaluator.Evaluator` object for the Hay protocol.
    
    Sets up an evaluator object for the Hay protocol, including measuring functions for bAP and BAC stimuli.
    
    Args:
        step (bool): Whether to include step current measurements (not implemented yet).
        vInit (bool): Whether to include vInit measurements. (not implemented yet)
        bAP_kwargs (dict): Keyword arguments for the bAP measurement function.
        BAC_kwargs (dict): Keyword arguments for the BAC measurement function.
        interpolate_voltage_trace (bool): Whether to interpolate the voltage trace to a fixed time interval.
        
    Returns:
        (:class:`~biophysics_fitting.evaluator.Evaluator`): An evaluator object.
        
    Raises:
        NotImplementedError: If :paramref:step or :paramref:vInit are set to True.
        
    Note:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    e = Evaluator()
    bap = hay_evaluation_python.bAP(**bAP_kwargs)
    bac = hay_evaluation_python.BAC(**BAC_kwargs)

    if interpolate_voltage_trace:
        e.setup.pre_funs.append(interpolate_vt)

    e.setup.evaluate_funs.append(
        ['BAC.hay_measure', bac.get, 'BAC.hay_features'])

    e.setup.evaluate_funs.append(
        ['bAP.hay_measure', bap.get, 'bAP.hay_features'])

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


def get_Combiner(step=False):
    """Get a set up :class:`~biophysics_fitting.combiner.Combiner` object for the Hay protocol.
    
    Args:
        step (bool): Whether to include step current measurements.
        
    Returns:
        (:class:`~biophysics_fitting.combiner.Combiner`): A combiner object.
        
    Note:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    return hay_complete_default_setup.get_Combiner(step=step)


from . import hay_complete_default_setup