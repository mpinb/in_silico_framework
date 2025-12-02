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

"""Inject a step current at the soma."""

from biophysics_fitting.setup_stim import setup_soma_step


def soma_current_injection(cell, amplitude=None, delay=None, duration=None):
    """Inject a step current at the soma.
    
    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        amplitude (float): The amplitude of the current (nA).
        delay (float): The delay of the current (ms).
        duration (float): The duration of the current (ms).

    Returns:
        :py:class:`~single_cell_parser.cell.Cell`: The cell with the current injection set up.

    See also:
        :py:meth:`biophysics_fitting.setup_stim.setup_soma_step`
    """
    setup_soma_step(cell, amplitude=amplitude, delay=delay, duration=duration)
    return cell
