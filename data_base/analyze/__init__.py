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
"""Analyze simrun-initialized databases.

This module provides methods for binning and aggregating synapse activations, spike times, and voltage traces, as well
as convenience methods to analyze the results of :mod:`simrun.reduced_model`.

See also:
    :mod:`data_base.db_initializers.load_simrun_general` for initializing databases from :mod:`simrun` results.
"""


from .spike_detection import spike_detection
from . import spatiotemporal_binning
import logging
logger = logging.getLogger("ISF").getChild(__name__)
from config.user.cell_types import EXCITATORY, INHIBITORY

def split_synapse_activation(
    sa,
    selfcheck=True,
    excitatory=EXCITATORY,
    inhibitory=INHIBITORY):
    '''Augment a :ref:`syn_activation_format` dataframe with a boolean column for excitatory/inhibitory.
    
    Args:
        sa (:class:`~pandas.DataFrame`): 
            A :ref:`syn_activation_format` dataframe.
            Must contain the column ``synapse_type``.
        selfcheck (bool): If ``True``, check if all cell types are either excitatory or inhibitory.
        excitatory (list): List of excitatory cell types.
        inhibitory (list): List of inhibitory cell types.
        
    Returns:
        tuple: a :class:`~pandas.DataFrame` with excitatory synapse activations, and one for inhibitory synapse activations.
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
