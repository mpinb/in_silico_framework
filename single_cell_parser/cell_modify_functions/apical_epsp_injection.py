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

"""Injects an epsp-shaped current at a certain distance from the soma."""

from biophysics_fitting.setup_stim import setup_apical_epsp_injection as setup_apical_epsp_injection_


def apical_epsp_injection(
        cell,
        dist=None,
        amplitude=None,
        delay=None,
        rise=1.0,
        decay=5):
    '''Injects an epsp-shaped current at a certain distance from the soma.

    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        dist (float): The distance from the soma (um).
        amplitude (float): The amplitude of the current (nA).
        delay (float): The delay of the current (ms).
        rise (float): The rise time of the epsp (ms).
        decay (float): The decay time of the epsp (ms).

    Returns:
        :py:class:`~single_cell_parser.cell.Cell`: The cell with the current injection set up.

    See also:
        :py:meth:`biophysics_fitting.setup_stim.setup_apical_epsp_injection`     
    '''
    setup_apical_epsp_injection_(
        cell,
        dist=dist,
        amplitude=amplitude,
        delay=delay,
        rise=rise,
        decay=decay)
    return cell
