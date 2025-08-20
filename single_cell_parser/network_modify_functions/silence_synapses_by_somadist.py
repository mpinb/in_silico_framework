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

"""Modify network activity by silencing synapses based on soma distance.

These functions can be used in e.g. :py:mod:`simrun.rerun_db` to re-simulate a network with modified activity patterns,
silencing synapses based on their postsynaptic location.
"""

import single_cell_parser.analyze as sca


def silence_synapses_by_somadist(cell, evokedNW, soma_dist_ranges=None):
    '''
    Silence synapses at a certain soma distance.
    
    Args:
        cell (:py:class:`single_cell_parser.cell.Cell`): The cell to modify.
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
