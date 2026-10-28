# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Convenience functions for the :py:mod:`~biophysics_fitting.exploration_from_seedpoint` module."""

import logging
import os
import sys

import numpy as np
import pandas as pd
import six

logger = logging.getLogger("ISF").getChild(__name__)

class silence_stdout():
    '''Silence stdout.
    
    Can be used as context manager (``with silence_stdout():``) and decorator (``@silence_stdout()``).

    See also:
        https://stackoverflow.com/a/2829036/5082048
    '''

    def __init__(self):
        self.save_stdout = sys.stdout

    def __enter__(self):
        logging.disable(logging.CRITICAL)
        sys.stdout = six.StringIO()
        
    def __exit__(self, *args, **kwargs):
        logging.disable(logging.NOTSET)
        sys.stdout = self.save_stdout
        
    def __call__(self, func):
        def wrapper(*args, **kwds):
            with self:
                return func(*args, **kwds)
        return wrapper
    
def read_df_file(path, robust=False):
    """
    Read a dataframe saved as ``.pickle`` or ``.parquet``, depending on the file extension.
    If ``robust`` and it cannot be read, still return a dataframe, containing an error as content.
    Useful for when you don't want your code to error during some large-scale analysis.

    Args:
        path (str): path to the ``.pickle`` or ``.parquet`` dataframe
        robust (bool): whether to return a dataframe containing the error instead of raising if the file cannot be read.
            An unsupported file extension raises regardless.

    Returns:
        pd.DataFrame: the stored DataFrame if reading was successful, otherwise a single-row DataFrame
        holding only the error in the column 'init_error'. If ``robust``, a successfully read DataFrame
        always contains the column 'init_error', added as '' if missing (stored values are kept).
        Otherwise, it is returned exactly as stored.

    Raises:
        ValueError: if the file extension is neither ``.pickle`` nor ``.parquet``.
    """
    readers = {'.pickle': pd.read_pickle, '.parquet': pd.read_parquet}
    extension = os.path.splitext(path)[1]
    if extension not in readers:
        raise ValueError(f'Cannot read {path}: file extension must be one of {list(readers)}')
    try:
        df = readers[extension](path)
    except Exception as e:
        if not robust:
            raise
        logger.warning(f'Could not read {path}: {e!r}')
        return pd.DataFrame({'init_error': [f'Could not read {path}: {e!r}']})
    if robust and 'init_error' not in df.columns:
        df['init_error'] = ''
    return df

def read_particle_df(seed_folder, particle_id, robust=True, file_types=('.pickle', '.parquet')):
    """
    Read the results of a single particle of a RW exploration.
    
    Args:
        seed_folder (str): the path of the directory corresponding to a seedpoint.
        particle_id (str): the particle id
        robust (bool): whether unreadable files are replaced by a row containing the error instead of raising, 
            see :py:func:`~biophysics_fitting.exploration_from_seedpoint.utils.read_df_file`.
        file_types (tuple): the file extensions to read.
        
    Returns:
        pd.DataFrame | str: The results of the RW exploration of a single particle, ordered by the
        iteration number in the file names, with added 'iteration' (row count) and 'particle_id'
        columns. If ``robust``, it is guaranteed to contain an 'init_error' column.
        'empty' if the particle has no result files.
    """
    path = os.path.join(seed_folder, str(particle_id))
    df_names = [p for p in os.listdir(path) if p.endswith(tuple(file_types))]
    df_names = sorted(df_names, key=lambda x: int(x.split('.')[0]))
    dfs = [read_df_file(os.path.join(path, p), robust=robust) for p in df_names]
    if len(dfs) == 0:
        return 'empty'
    df = pd.concat(dfs).reset_index(drop=True)
    df['iteration'] = df.index
    df['particle_id'] = particle_id
    return df


def get_vector_norm(v):
    """Calculate the norm of a vector v.
    
    Args:
        v (np.array): Vector
        
    returns:
        float: Norm of the vector"""
    return np.sqrt(sum(v**2))

def evaluation_function_incremental_helper(
        p,
        *,
        s = None,  
        e = None,
        cutoffs = None,
        stim_order, 
        verbose = True,
        additional_evaluation_functions = None,
        objectives_by_stimulus = None,
        stim_run_name_mapping = None):
    '''Evaluate a model one stimulus at a time, stopping early if a stimulus exceeds its cutoff.
    
    This is useful for performace, as it allows to run the fastest simulations first,
    and provides an early stopping criterion if a model is not able to match these objectives.

    Only simulator outputs whose names end in ``measure`` (e.g. ``BAC.hay_measure``) are passed to the Evaluator.
    Other outputs (e.g. ``BAC.range_vars``) are only passed to the additional evaluation functions.

    Args:
        p (dict | pd.Series): Biophysical parameters of the model. Copied before simulation.
        s (:class:`~biophysics_fitting.simulator.Simulator`): Simulator object
        e (:class:`~biophysics_fitting.evaluator.Evaluator`): Evaluator object
        cutoffs (Dict[str,float], optional): 
            Keys (str) must appear in stim_order and objectives_by_stimulus. 
            Values (float) indicate the maximum error allowed for these stimuli.
            A stimulus fails if any of its objectives exceeds the cutoff or is NaN.
            Stimuli without a cutoff are evaluated but never cause an early stop.
            Default: None (no cutoffs).
        stim_order ([str] | [(str)]):
            Order in which stimuli are simulated. 
            List consisting of strings and tuples of strings. 
            Use strings if only one stimulus is to be simulated.
            Use tuples of strings to simulate several stimuli in one go. 
        verbose (bool, optional): If True, prints which stimulus is evaluated and why evaluation stops. Default: True.
        additional_evaluation_functions (list, optional): additional functions to be applied onto the final voltage 
            traces dictionary, which return a dictionary which is appended to the
            evaluations. Only applied if all stimuli pass. Default: None (no additional functions).
        objectives_by_stimulus (Dict[str,list], optional): 
            Keys (str) must appear in stim_order. 
            Values (list) are objective names returned by the evaluator object.
            Required if cutoffs are given.
        stim_run_name_mapping (Dict[str, str | (str)], optional): 
            Maps names in stim_order to the stimulus name or tuple of stimulus names passed to the Simulator.
            This allows grouped protocols to be referred to by one name in stim_order, cutoffs and objectives_by_stimulus.
            Names not in the mapping are passed to the Simulator unchanged.
            Default: None (no mapping).
    
    Returns: 
        Tuple[bool, dict]: 
            ``True`` if all stimuli pass, ``False`` if at least one stimulus has an error above its cutoff.
            The dictionary contains the input parameters ``p`` and the objective values returned by the evaluator.
            If all stimuli pass, it also contains the output of the additional evaluation functions.
            On an early stop, it only contains the objectives of the stimuli evaluated so far.
    '''
    additional_evaluation_functions = additional_evaluation_functions or []
    cutoffs = cutoffs or {}
    stim_run_name_mapping = stim_run_name_mapping or {}
    assert s is not None, "Please provide a Simulator object"
    assert e is not None, "Please provide an Evaluator object"
    assert not cutoffs or objectives_by_stimulus is not None, "Please provide objectives_by_stimulus to apply cutoffs"
    # make sure all defined cutoffs can actually be applied
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
        with silence_stdout():
            voltage_traces_ = s.run(p, stims = stim_run_name_mapping.get(stim, stim))
            voltage_traces.update(voltage_traces_)
            # only pass voltage traces to the evaluator. these are saved with "measure" suffix by convention
            # other outputs (e.g. ranges) are only passed to the additional evaluation functions

            voltage_traces_for_evaluation = {k: v for k, v in voltage_traces_.items() if k.endswith('measure')}
            evaluation_ = e.evaluate(voltage_traces_for_evaluation, raise_ = False)
            evaluation.update(evaluation_)
        if stim in cutoffs:
            error = pd.Series(evaluation_)[objectives_by_stimulus[stim]].max(skipna=False)
            if np.isnan(error) or error > cutoffs[stim]:
                if verbose: 
                    print('stimulus', stim, 'has an error of', error, '- skipping further evaluation')
                return False, evaluation
    if verbose:
        print('all stimuli successful!')
    for aef in additional_evaluation_functions:
        evaluation.update(aef(voltage_traces))
    return True, evaluation

def convert_all_check_columns_bool_to_float(df): 
    '''Convert all boolean values to float in a pandas dataframe.
    
    Only does this for columns that have ``"check"`` in the column name.
    
    Args:
        df (pd.DataFrame): DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with boolean values converted to float.
    '''
    check_columns = [col for col in df.columns if 'check' in col]
    for col in check_columns: 
        #otherwise the 'True' strings cannot be converted to float and cannot map to bool bc NaN 
        df[col] = df[col].replace(to_replace = 'True', value = 1.0)
        df[col] = df[col].replace(to_replace = 'False', value = 0.0)
        df[col] = df[col].replace({None:np.nan})
        df[col] = df[col].map(float) 
    return df
