import numpy as np
import pandas as pd
from data_base.utils import silence_stdout


def get_vector_norm(v):
    """Calculate the norm of a vector v.
    
    Args:
        v (np.array): Vector
        
    returns:
        float: Norm of the vector"""
    return np.sqrt(sum(v**2))

def evaluation_function_incremental_helper(
        p,
        s = None,  
        e = None,
        cutoffs = None,
        stim_order = None, 
        verbose = True,
        additional_evaluation_functions = None,
        objectives_by_stimulus = None):
    '''Evaluate a model shows one stimulus at a time.
    
    This is useful for performace, as it allows to run the fastest simulations first,
    and provides an early stopping criterion if a model is not able to match these objectives.

    Args:
        s (:class:`biophysics_fitting.simulator.Simulator`): Simulator object
        e (:class:`biophysics_fitting.evaluator.Evaluator`): Evaluator object
        stim_order ([str] | [(str)]):
            Order in which stimuli are simulated. 
            List consisting of strings and tuples of strings. 
            Use strings if only one stimulus is to be simulated.
            Use tuples of strings to simulate several stimuli in one go. 
        cutoffs ({str: float}): 
            Keys (str) must appear in stim_order. 
            Values (float)indicate the maximum error allowed for these stimuli
        objectives_by_stimulus ({str: list}): 
            Keys (str) must appear in stim_order. 
            Values (list) are objective names returned by the evaluator object.
        additional_evaluation_functions (list): additional functions to be applied onto the final voltage 
            traces dictionary, which return a dictionary which is appended to the
            evaluations. 
    
    Returns: 
        True if all stimuli pass. False if at least one stimulus has an error above its cutoff. 
    '''
    # make sure all defined cutoffs can actually be applied
    additional_evaluation_functions = additional_evaluation_functions or []
    cutoffs = cutoffs or []
    assert s is not None, "Please provide a Simulator object"
    assert e is not None, "Please provide an Evaluator object"
    for c in cutoffs:
        assert c in stim_order
        assert c in objectives_by_stimulus

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
            print("traces: ", voltage_traces_for_evaluation)
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

def convert_all_check_columns_bool_to_float(df): 
    '''returns modified df'''
    check_columns = [col for col in df.columns if 'check' in col]
    for col in check_columns: 
        #otherwise the 'True' strings cannot be converted to float and cannot map to bool bc NaN 
        df[col] = df[col].replace(to_replace = 'True', value = 1.0)
        df[col] = df[col].replace(to_replace = 'False', value = 0.0)
        df[col] = df[col].replace({None:np.nan})
        df[col] = df[col].map(float) 
    return df
