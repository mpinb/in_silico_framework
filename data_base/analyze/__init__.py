# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.
"""Analyze simrun-initialized databases.

This module provides methods for binning and aggregating synapse activations, spike times, and voltage traces, as well
as convenience methods to analyze the results of :py:mod:`simrun.reduced_model`.

See also:
    :py:mod:`data_base.db_initializers.load_simrun_general` for initializing databases from :py:mod:`simrun` results.
"""


from .spike_detection import spike_detection
from . import spatiotemporal_binning
import logging
logger = logging.getLogger("ISF").getChild(__name__)
from config.cell_types import EXCITATORY, INHIBITORY

def split_synapse_activation(
    sa,
    selfcheck=True,
    excitatory=EXCITATORY,
    inhibitory=INHIBITORY):
    '''Augment a :ref:`syn_activation_format` dataframe with a boolean column for excitatory/inhibitory.
    
    Args:
        sa (:py:class:`~pandas.DataFrame`): 
            A :ref:`syn_activation_format` dataframe.
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