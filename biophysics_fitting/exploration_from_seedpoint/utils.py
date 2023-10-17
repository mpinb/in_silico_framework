import numpy as np
import pandas as pd
from model_data_base.utils import silence_stdout


def get_vector_norm(v):
    return np.sqrt(sum(v**2))

def evaluation_function_incremental_helper(p,
                                           s = None,  
                                           e = None,
                                           cutoffs = {'bAP':3.2, 
                                                  'BAC': 3.2, 
                                                  'StepOne':4.5, 
                                                  'StepTwo': 4.5, 
                                                  'StepThree': 4.5},
                                           stim_order = ['bAP', 'BAC', 'StepOne', 'StepTwo', 'StepThree'], 
                                           verbose = True,
                                           additional_evaluation_functions = [],
                                           objectives_by_stimulus = None):
    '''
    global variables: 
    evaluators_by_stimulus
    objectives_dict
    '''
    p = p.copy()
    evaluation = {}
    evaluation.update(p)
    voltage_traces = {}
    for stim in stim_order:
        if verbose:
            print('evaluating stimulus', stim)
        with silence_stdout:
            voltage_traces_ = s.run(p, stims = stim)
            voltage_traces.update(voltage_traces_)
            # this is currently specific to the hay simulator / evaluator, which gets confused if 
            # any voltage traces beyond what it expects are present
            # thus filter it out and have a 'clean' voltage_traces_for_evaluation
            voltage_traces_for_evaluation = {k:v for k,v in voltage_traces_.items() if k.endswith('hay_measure')}
            evaluation_ = e.evaluate(voltage_traces_for_evaluation, raise_ = False)
            evaluation.update(evaluation_)
        if stim in cutoffs:
            error = max(pd.Series(evaluation_)[objectives_by_stimulus[stim]])
            if error > cutoffs[stim]:
                if verbose: 
                    print('stimulus', stim, 'has an error of', error, '- skipping further evaluation')
                return False, evaluation
    if verbose:
        print('all stimuli successful!')
    for aef in additional_evaluation_functions:
        evaluation.update(aef(voltage_traces))
    return True, evaluation