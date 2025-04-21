
import os, sys, json
import Interface as I
from project_specific_ipynb_code.morphology_transition.cell_parser import create_cell

# evaluation_function_incremental_helper, but with new return_faulty_voltage_trace option
def evaluation_function_incremental_helper(p,
                                           s = None,  
                                           e = None,
                                           cutoffs = None,
                                           stim_order = None, 
                                           verbose = True,
                                           additional_evaluation_functions = [],
                                           objectives_by_stimulus = None,
                                           return_faulty_voltage_trace = False,
                                           print_ = print):
    '''
    Allows to evaluate if a model shows responses with errors below the cutoff, one
    stimulus at a time. 
    
    Returns: True if all stimuli pass. False if any stimulus has an error above its cutoff. 
    
    s: Simulator object
    e: Evaluator object
    stim_order: order in which stimuli are simulated. List consisting of strings 
        and tuples of strings. Use strings if only one stimulus is to be simulated, 
        use tuples of strings to simulate several stimuli in one go. 
    cutoffs: dictionary, with keys that are in stim_order. Values are float and 
        indicate the maximum error allowed for these stimuli
    objectives_by_stimulus: dictionary with keys that are in stim_order. Values are lists 
        of names of objectives, returned by the evaluator object.
    additional_evaluation_functions: additional functions to be applied onto the final voltage 
        traces dictionary, which return a dictionary which is appended to the
        evaluations. 
    '''
    silence_stdout = I.silence_stdout
    import pandas as pd
    import numpy as np
    import time
    # make sure all defined cutoffs can actually be applied
    for c in cutoffs:
        assert(c in stim_order)
        assert(c in objectives_by_stimulus)
    p = p.copy()
    evaluation = {}
    evaluation.update(p)
    voltage_traces = {}
    t0 = time.time()
    for stim in stim_order:
        if verbose:
            print_(f'evaluating stimulus {stim}')
        with silence_stdout:
            t0 = time.time()
            voltage_traces_ = s.run(p, stims = stim)
            t1 = time.time()
            voltage_traces.update(voltage_traces_)
            # this is currently specific to the hay simulator / evaluator, which gets confused if 
            # any voltage traces beyond what it expects are present
            # thus filter it out and have a 'clean' voltage_traces_for_evaluation
            voltage_traces_for_evaluation = {k:v for k,v in voltage_traces_.items() if k.endswith('hay_measure')}
            evaluation_ = e.evaluate(voltage_traces_for_evaluation, raise_ = False)
            evaluation.update(evaluation_)
            t2 = time.time()
        print(f'times: {t1-t0:.2f}s (simulation), {t2-t1:.2f}s (evaluation), {t2-t0:.2f}s (all)')
        if stim in cutoffs:
            error = max(pd.Series(evaluation_)[objectives_by_stimulus[stim]])
            if error > cutoffs[stim]:
                if verbose: 
                    print_(f'stimulus {stim} has an error of {error} - skipping further evaluation')
                if return_faulty_voltage_trace:
                    return False, evaluation, voltage_traces_for_evaluation
                else:
                    return False, evaluation
    if verbose:
        print_('all stimuli successful!')
    for aef in additional_evaluation_functions:
        evaluation.update(aef(voltage_traces))
    if return_faulty_voltage_trace:
        return True, evaluation, None
    else:
        return True, evaluation

# boring helper functions
def get_morph_str(id_):
    if str(id_) in ['64','71','69']:
        return f'WR{id_}'
    return str(id_)

def log_and_print(logfile, s):
    print(s)
    with open(logfile, 'a') as f:
        f.write(f'{s}\n')
        f.flush()

def plot_vt(vt):
    fig = I.plt.figure()
    ax = fig.add_subplot(111)
    for k in vt.keys():
        t = vt[k]['tVec']
        vs = vt[k]['vList']
        for v in vs:
            ax.plot(t, v)
    return fig

# avoid any file locks when reading from mdb
class NoLockMdb:
    '''bypassing the sqllite stuff, relying on file name conventions. no locks needed.'''
    def __init__(self, path):
        self.path = path
        self.flist = os.listdir(self.path)
        assert 'sqlitedict.db' in self.flist
        
    def __getitem__(self, key):
        import cloudpickle
        folder = [f for f in self.flist if key.lower() == f[:-10]]
        assert len(folder) == 1
        folder = folder[0]
        folder = os.path.join(self.path, folder)
        if 'db.core' in os.listdir(folder):
            return NoLockMdb(folder)
        with open(os.path.join(folder, 'Loader.pickle'), 'rb') as f:
            return cloudpickle.load(f).get(folder)    
        
    def keys(self):
        return [k[:-10] for k in self.flist if k.endswith('_')]

# # exploration helper functions
# def get_p_proposal(p, step_size):
#     p = p[param_names]
#     # delta in normalized space
#     p_delta = I.np.random.randn(len(p)) # draw from rotation symmetric pdf
#     p_delta = p_delta/I.np.sqrt(sum(p_delta**2)) # unit length
#     p_delta = p_delta*step_size # step_size length
#     # normalize
#     p = (p-mi_)/(ma_-mi_) 
#     # apply delta
#     p = p+p_delta
#     # cap
#     p[p<0] = 0
#     p[p>1] = 1
#     # unnormalize
#     return p*(ma_-mi_)+mi_

def params2array(savelist, result, additional = []):
    # always same order, nan if not computed
    save_array = [result[k] if k in result else float('nan') for k in savelist] 
    # metadata
    save_array = save_array + additional
    # must all be same dtype - converts bools
    save_array = [float(x) for x in save_array] 
    # must be numpy, must be row
    save_array = I.np.array(save_array).reshape(1,-1) 
    # doublecheck
    assert save_array.dtype == I.np.dtype('float64')
    return save_array

def array2params(savelist, arr):
    assert len(arr) >= len(savelist)
    s = I.pd.Series(arr[:len(savelist)], savelist)
    additional = list(arr[len(savelist):])
    return s, additional
