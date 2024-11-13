"""Analyze simrun-initialized databases.

This module provides methods for binning and aggregating synapse activations, spike times, and voltage traces, as well
as convenience methods to analyze the results of :py:mod:`simrun.reduced_model`.

See also:
    :py:mod:`data_base.isf_data_base.db_initializers.load_simrun_general` for initializing databases from :py:mod:`simrun` results.
"""


import barrel_cortex
from .spike_detection import spike_detection
from . import spatiotemporal_binning

excitatory = barrel_cortex.excitatory
inhibitory = barrel_cortex.inhibitory


def split_synapse_activation(
    sa,
    selfcheck=True,
    excitatory=excitatory,
    inhibiotry=inhibitory):
    '''Augment a :ref:`synapse_activation_format` dataframe with a boolean column for excitatory/inhibitory.
    
    Args:
        sa (:py:class:`~pandas.DataFrame`): 
            A :ref:`synapse_activation_format` dataframe.
            Must contain the column ``synapse_type``.
        selfcheck (bool): If ``True``, check if all cell types are either excitatory or inhibitory.
        excitatory (list): List of excitatory cell types.
        inhibitory (list): List of inhibitory cell types.
        
    Returns:
        tuple: a :py:class:`~pandas.DataFrame` with excitatory synapse activations, and one for inhibitory synapse activations.
    '''
    if selfcheck:
        celltypes = sa.apply(
            lambda x: x.synapse_type.split('_')[0], 
            axis=1).drop_duplicates()
        for celltype in celltypes:
            assert celltype in excitatory + inhibitory

    sa['EI'] = sa.apply(
        lambda x: 'EXC'
        if x.synapse_type.split('_')[0] in excitatory else 'INH',
        axis=1)
    return sa[sa.EI == 'EXC'], sa[sa.EI == 'INH']