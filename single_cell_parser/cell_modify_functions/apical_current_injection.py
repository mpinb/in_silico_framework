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

"""Inject a current at a given distance from the soma."""

from biophysics_fitting.setup_stim import setup_soma_step


def apical_current_injection(
        cell,
        amplitude=None,
        delay=None,
        duration=None,
        dist=None):
    """Inject a current at a given distance from the soma.
    
    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        amplitude (float): The amplitude of the current (nA).
        delay (float): The delay of the current (ms).
        duration (float): The duration of the current (ms).
        dist (float): The distance from the soma (um).
            For an apical current injection, this should be the distance from the soma to the apical dendrite.
    
    Returns:
        :py:class:`~single_cell_parser.cell.Cell`: The cell with the current injection set up.

    See also:
        :py:meth:`biophysics_fitting.setup_stim.setup_soma_step`
    """
    # note: setup_soma_step has been extended to support a dist parameter
    setup_soma_step(
        cell,
        amplitude=amplitude,
        delay=delay,
        duration=duration,
        dist=dist)
    return cell
