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
