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
"""
Configure label names for :ref:`hoc_file_format` and :ref:`swc_file_format` morphology files.
"""

HOC_LABEL_MAP = {
    'soma':          'Soma',
    'dend':          'Dendrite',
    'basaldendrite': 'Dendrite',
    'basal':         'Dendrite',
    'apical':        'ApicalDendrite',
    'axon':          'Axon',
}
"""Mapping between labels found in :ref:`hoc_file_format` morphology files or connections spreadsheets, and the label to be used internally throughout ISF.
Labels are matched based on a case-insensitive basis.

For example, if a :ref:`hoc_file_format` contains the label "DEND", "Dend", or "BasalDendrite", these will be converted in ISF to just "Dendrite".
If a connections spreadsheet contains labels "BASAL", it will be converted to "Dendrite".
"""
