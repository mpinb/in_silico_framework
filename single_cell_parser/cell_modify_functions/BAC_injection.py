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