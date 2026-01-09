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

'''Injects the BAC stimulus :cite:`Hay_Hill_Schuermann_Markram_Segev_2011` at a specified distance.'''
from biophysics_fitting.setup_stim import setup_BAC


def BAC_injection(cell, dist=None):
    '''Injects the BAC stimulus :cite:`Hay_Hill_Schuermann_Markram_Segev_2011` at a specified distance.

    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell object.
        dist (float): The distance from the soma (um).
    
    Returns:
        :class:`~single_cell_parser.cell.Cell`: The cell with the current injection set up.

    See also:
        :py:meth:`biophysics_fitting.setup_stim.setup_BAC`
    '''
    setup_BAC(cell, dist=dist)
    return cell
