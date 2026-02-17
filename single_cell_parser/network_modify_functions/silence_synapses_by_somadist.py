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

"""Modify network activity by silencing synapses based on soma distance.

These functions can be used in e.g. :mod:`simrun.rerun_db` to re-simulate a network with modified activity patterns,
silencing synapses based on their postsynaptic location.
"""

import single_cell_parser.analyze as sca


def silence_synapses_by_somadist(cell, evokedNW, soma_dist_ranges=None):
    '''
    Silence synapses at a certain soma distance.
    
    Args:
        cell (:class:`single_cell_parser.cell.Cell`): The cell to modify.
        soma_dist_ranges (dict): Dictionary with synapse types as keys (e.g. L5tt_C2) and the range 
            in which it should be silenced as value. 
            
    Example:
        >>> soma_dist_ranges = {
        ... 'VPM_C2': [0,200],
        ... 'L5tt_C2': [1000,1200]
        ... }
    '''

    assert soma_dist_ranges is not None

    import six
    for synapse_type, ranges_ in six.iteritems(soma_dist_ranges):
        try:
            synapses = cell.synapses[synapse_type]
        except KeyError:
            print('skipping', synapse_type,
                  '(no connected cells of that type present)')
        distances = sca.compute_syn_distances(cell, synapse_type)
        min_, max_ = ranges_
        for syn, dist in zip(synapses, distances):
            if min_ <= dist < max_:
                syn.disconnect_hoc_synapse()
