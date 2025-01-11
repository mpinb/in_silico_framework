'''
This module provides methods to run Hay's stimulus protocols, and evaluate the resulting voltage traces.
'''


import os
from collections import defaultdict
import numpy as np
import pandas as pd
import neuron
h = neuron.h
import warnings
import sys
import contextlib, io
import logging
from .utils import StreamToLogger

logger = logging.getLogger("ISF").getChild(__name__)
# moved to the bottom to resolve circular import
# from .hay_complete_default_setup import get_hay_problem_description, get_hay_objective_names, get_hay_params_pdf

__author__ = 'Arco Bast'
__date__ = '2018-11-08'

neuron_basedir = os.path.join(os.path.dirname(__file__), 'MOEA_EH_minimal')


def setup_hay_evaluator():
    '''Set up the NEURON simulator environment for evaluation.
    
    This method adds a stump cell to the neuron environment, which is
    necessary to access the Hay evaluate functions. 
    It makes the following current stimuli available for NEURON:

        - bAP
        - BAC
        - SquarePulse (for the step currents)
    
    Args:
        testing (bool): If True, the function will test the reproducibility of the Hay evaluator.
        
    Returns:
        None
    
    Note:
        For the variable time step solver, this changes the step size and can 
        therefore minimally change the results. Before testing reproducability, 
        it is therefore necessary to initialize the evaluator.
        
    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
        
    '''
    # todo: this also creates a cell which is simulated in neuron
    # therefore the evaluator should be set up without
    # creating a cell
    #
    # also, this creates a lot of neuron variables
    import biophysics_fitting
    assert os.path.exists(neuron_basedir)
    import neuron
    h = neuron.h

    logger.warning(
        "Setting up hay evaluator. This loads several variables "
        "to the NEURON environment. Also, it creates an unconnected "
        "cell (which is very small ~ 1 compartment) which has the purpose "
        "to 'just be there' such that the functionality necessary to evaluate "
        "voltage traces is available. This has the side effect that in the "
        "case of the variable time step solver, the timesteps can be changed."
    )

    central_file_name = 'fit_config_89_CDK20050712_BAC_step_arco_run1.hoc'

    with StreamToLogger(
            logger, 10) as sys.stdout:  # redirect to log with level DEBUG (10)
        try:
            neuron.h.central_file_name
            if not neuron.h.central_file_name == central_file_name:
                raise ValueError(
                    'Once the central_file_name is set, it cannot be changed!')
        except AttributeError:
            #print 'setting up NEURON config'
            h('chdir("{path}")'.format(path=neuron_basedir))
            h('strdef central_file_name')
            h('central_file_name = "{}"'.format(central_file_name))
            h('''load_file("MOEA_gui_for_objective_calculation.hoc")''')


def is_setup():
    """Check if the NEURON environment is set up for the Hay evaluator.
    
    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information."""
    import neuron
    h = neuron.h
    try:
        neuron.h.central_file_name
        return True
    except AttributeError:
        return False


objectives_step = [
    'AI1', 'AI2', 'AI3', 'APh1', 'APh2', 'APh3', 'APw1', 'APw2', 'APw3', 'DI1',
    'DI2', 'ISIcv1', 'ISIcv2', 'ISIcv3', 'TTFS1', 'TTFS2', 'TTFS3', 'fAHPd1',
    'fAHPd2', 'fAHPd3', 'mf1', 'mf2', 'mf3', 'sAHPd1', 'sAHPd2', 'sAHPd3',
    'sAHPt1', 'sAHPt2', 'sAHPt3'
]

objectives_BAC = [
    'BAC_APheight', 'BAC_ISI', 'BAC_ahpdepth', 'BAC_caSpike_height',
    'BAC_caSpike_width', 'BAC_spikecount', 'bAP_APheight', 'bAP_APwidth',
    'bAP_att2', 'bAP_att3', 'bAP_spikecount'
]


def get_cur_stim(stim):
    """Get an input current stimulus from the Hay evaluator.
    
    Fetches either the bAP, BAC, or step current input stimuli from the Hay evaluator."""
    setup_hay_evaluator()
    sol = h.mc.get_sol()
    stim_count = len(sol)
    return {
        sol.o(cur_stim).get_name().s: cur_stim for cur_stim in range(stim_count)
    }[stim]


def hay_evaluate(cur_stim, tvec, vList):
    '''Evaluate a stimulus as described by :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`.
    
    Args:
        cur_stim (int): The stimulus to evaluate.
        tvec (list): The time vector.
        vList (list): The voltage list.
    
    Returns:
        dict: A dictionary with the feature names as keys and the feature values as values.
    
    Note: 
        I had the problem with python segfaulting as soon as this function got executed.
        In that case, make sure, the mechanisms are correctly compiled and loaded.
        You can load the mechanisms by importing the mechanisms module. - Arco
    '''
    setup_hay_evaluator()
    feature_mean_list = h.evaluator.feature_mean_list
    feature_std_list = h.evaluator.feature_std_list
    #tvec = h.evaluator.tvec
    #vList = h.evaluator.vList
    apc_vector = h.List()  #h.evaluator.apc_vector
    stim1 = h.evaluator.stim1  ### need to figure out, what this is ... seems to be unused in the distance calculator itself
    penalty = 250  # h.evaluator.penalty
    use_density = 0  # False # h.evaluator.use_density
    stimulus_feature_type_list = h.evaluator.stimulus_feature_type_list
    minspikenum = 2
    stim_vec = h.Vector(2)
    sol = h.mc.get_sol()

    if sol.o(cur_stim).get_type().s == "SquarePulse":
        stim_vec.x[0] = sol.o(cur_stim).get_numerical_parameter("Delay")  # 295
        stim_vec.x[1] = sol.o(cur_stim).get_numerical_parameter("Duration")  # 5
    elif sol.o(cur_stim).get_type().s == "bAP":
        stim_vec.x[0] = 295
        stim_vec.x[1] = 5
        minspikenum = 1
    elif sol.o(cur_stim).get_type().s == "BAC":
        stim_vec.x[0] = 295
        stim_vec.x[1] = 45

    hoc_tvec = h.Vector().from_python(tvec)
    hoc_vList = h.List()
    for v in vList:
        hoc_vList.append(h.Vector().from_python(v))

    with StreamToLogger(
            logger, 10) as sys.stdout:  # redirect to log with level DEBUG (10)
        try:
            x = h.calculator.get_organism_stimulus_error(
                feature_mean_list.o(cur_stim),
                feature_std_list.o(cur_stim),
                hoc_tvec,
                hoc_vList,
                apc_vector,  ## seems to be unused?
                stim1,
                penalty,
                use_density,
                cur_stim,  # $o4 argument
                stimulus_feature_type_list.o(cur_stim),
                stim_vec,
                minspikenum)
        except RuntimeError:
            # if incomplete simulation data is provided to the hay evaluate function,
            # this raises an hoc error
            return {
                k.s: 1000 for k in list(
                    h.evaluator.stimulus_feature_name_list.o(cur_stim))
            }

    return {
        h.evaluator.stimulus_feature_name_list.o(cur_stim).o(lv).s: x
        for lv, x in enumerate(x)
    }


# # cleanly startup distance calculator

# h('dir = "."')
# dir_ = '.'
# central_file_name = 'fit_config_86_CDK20041214_BAC_run5.hoc'
# mc = h.MOEAConfig(central_file_name, dir_)
# TargetTracePath = 'L5PC_2'
# tdc = h.TrajectoryDensityCalculator()
# calculator = h.DistanceCalculator(mc,dir_,TargetTracePath,tdc)
# #h('calculator = new DistanceCalculator(mc,dir,TargetTracePath,tdc)')

# x = calculator.get_organism_stimulus_error(feature_mean_list.o(cur_stim),
#                                            feature_std_list.o(cur_stim),
#                                            tvec,
#                                            vList,
#                                            apc_vector, ## seems to be unused?
#                                            stim1,
#                                            penalty,
#                                            use_density,
#                                            cur_stim, # $o4 argument
#                                            stimulus_feature_type_list.o(cur_stim),
#                                            stim_vec,
#                                            minspikenum)


def hay_evaluate_bAP(tVec=None, vList=None):
    """Evaluate the bAP stimulus.
    
    Args:
        tVec (list): The time vector.
        vList (list): The voltage list.
        
    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information."""
    cur_stim = get_cur_stim('bAP')
    return hay_evaluate(cur_stim, tVec, vList)


def hay_evaluate_BAC(tVec=None, vList=None):
    """Evaluate the BAC stimulus.
    
    See py:meth:`~biophysics_fitting.setup_stim.setup_BAC` for more info on the BAC stimulus.

    Args:
        tVec (list): The time vector.
        vList (list): The voltage list.
        
    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information."""
    cur_stim = get_cur_stim('BAC')
    return hay_evaluate(cur_stim, tVec, vList)


def hay_evaluate_StepOne(tVec=None, vList=None):
    """Evaluate the StepOne stimulus.
    
    See py:meth:`~biophysics_fitting.setup_stim.setup_StepOne` for more info on the StepOne stimulus.

    Args:
        tVec (list): The time vector.
        vList (list): The voltage list.
        
    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    cur_stim = get_cur_stim('StepOne')
    return hay_evaluate(cur_stim, tVec, vList)


def hay_evaluate_StepTwo(tVec=None, vList=None):
    """Evaluate the StepTwo stimulus.
     
    See py:meth:`~biophysics_fitting.setup_stim.setup_StepTwo` for more info on the StepTwo stimulus.

    Args:
        tVec (list): The time vector.
        vList (list): The voltage list.
        
    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """ 
    cur_stim = get_cur_stim('StepTwo')
    return hay_evaluate(cur_stim, tVec, vList)


def hay_evaluate_StepThree(tVec=None, vList=None):
    """Evaluate the StepThree stimulus.
    
    See py:meth:`~biophysics_fitting.setup_stim.setup_StepThree` for more info on the StepThree stimulus.
    
    Args:
        tVec (list): The time vector.
        vList (list): The voltage list.
        
    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    cur_stim = get_cur_stim('StepThree')
    return hay_evaluate(cur_stim, tVec, vList)


from .hay_complete_default_setup import get_hay_problem_description, get_hay_objective_names, get_hay_params_pdf
