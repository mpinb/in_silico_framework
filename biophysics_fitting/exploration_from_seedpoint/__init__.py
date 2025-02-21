"""
Explore viable biophysical models from a given seedpoint.
Given the following empirical constraints:

- a set of biophysical parameters
- a morphology
- empirically recorded responses to defined stimulus protocols (see e.g. :py:meth:`biophysics_fitting.hay_specification.get_hay_problem_description`).

this package provides methods and full workflows that allow you to make random variations on the input biophysical parameters, 
run the stimulus protocols on the cell, and evaluate how much they deviate from the empirically recorded mean.
Eventually, this random walk through parameter space can explore very diverse biophysical models that are all within the empirical constraints.
"""
from functools import partial
import os
import pandas as pd
import numpy as np
import cloudpickle
import shutil
from .utils import get_vector_norm
from data_base.utils import silence_stdout
import time
import sys

def evaluation_function_incremental_helper(
        p,
        s = None,  
        cutoffs = None,
        stim_order = ['bAP', 'BAC', 'StepOne', 'StepTwo', 'StepThree'], 
        verbose = True,
        evaluators_by_stimulus = None,
        additional_evaluation_functions = [],
        objectives_by_stimulus = None):
    '''
    Helper function for the evaluation function. 
    As soon as a single stimulus shows that a biophysical model does not match the objectives,
    it is not necessary to evaluate the other stimuli.
    This method runs the evaluation functions one by one and exits prematurely as soon as an objective
    is above the desired cutoff defined in :paramref:`cutoffs`.
    
    Args:
        p (dict | :py:class:`pandas.Series`): Parameter values used in the simulation. See :py:mod:`~biophysics_fitting.hay_complete_default_setup` for an example.
        s (Simulator): Simulator object.
        cutoffs (dict): Dictionary with keys that are in :paramref:`stim_order`. Values are floats that define a maximum allowed error for any objective corresponding to that stimulus.
            Note that each stimulus evokes a voltage trace that is parametrized by multiple objectives, each with their own error.
            This method checks if the largest error exceeds some value.
            Default: {'bAP':3.2, 'BAC': 3.2, 'StepOne':4.5, 'StepTwo': 4.5, 'StepThree': 4.5}, as used in :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`
        stim_order (array-like): Order in which stimuli are simulated.
            Default: ['bAP', 'BAC', 'StepOne', 'StepTwo', 'StepThree'], which is the order of stimuli used in :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`
        verbose (bool): If True, print intermediate results.
        evaluators_by_stimulus (dict): Dictionary with keys that are in :paramref:`stim_order`. Values are evaluators that are used to evaluate the voltage traces.
        additional_evaluation_functions (list): List of functions that are called after the voltage traces are evaluated. The results are added to the evaluation dict, and returned.
        objectives_by_stimulus (dict): Dictionary with keys that are in :paramref:`stim_order`. Values are lists of objectives that are used to evaluate the voltage traces.
        
    Returns:
        tuple: (bool, dict). The first value is True if all stimuli are within the cutoffs, False otherwise.
            The second value is a dictionary with the evaluation results.
    '''
    
    if stim_order is None:
        # Default value: :cite:`Hay_Hill_Schuermann_Markram_Segev_2011`
        stim_order = ['bAP', 'BAC', 'StepOne', 'StepTwo', 'StepThree']

    cutoffs = cutoffs or {
            'bAP':3.2, 
            'BAC': 3.2, 
            'StepOne':4.5, 
            'StepTwo': 4.5,
            'StepThree': 4.5}

    p = p.copy()
    evaluation = {}
    evaluation.update(p)
    voltage_traces = {}
    for stim in stim_order:
        if verbose:
            print('evaluating stimulus', stim)
        with silence_stdout:
            voltage_traces_ = s.run(p, stims=[stim])
            voltage_traces.update(voltage_traces_)
            # this is currently specific to the hay simulator / evaluator, which gets confused if
            # any voltage traces beyond what it expects are present
            # thus filter it out and have a 'clean' voltage_traces_for_evaluation
            voltage_traces_for_evaluation = {
                k: v
                for k, v in voltage_traces.items()
                if k.endswith('hay_measure')
            }
            e = evaluators_by_stimulus[stim]
            evaluation_ = e.evaluate(voltage_traces_for_evaluation)
            evaluation.update(evaluation_)
        error = max(pd.Series(evaluation_)[objectives_by_stimulus[stim]])
        if error > cutoffs[stim]:
            if verbose:
                print('stimulus', stim, 'has an error of', error,
                      '- skipping further evaluation')
            #for k in full_evaluation_keys:
            #    if not k in evaluation:
            #        evaluation[k] = float('nan')
            return False, evaluation
    if verbose:
        print('all stimuli successful!')
    for aef in additional_evaluation_functions:
        evaluation.update(aef(voltage_traces))
    return True, evaluation