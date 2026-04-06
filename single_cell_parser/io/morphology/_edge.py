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
from __future__ import annotations
from typing import List
import numpy

class _Edge(object):
    r'''Convenience class for NEURON segments.

    Private class used in :func:`~single_cell_parser.reader.read_hoc_file` to store information about a single morphological segment spanning from point to point.
    These edges should not be used as API to neuron segments or sections - they merely serve as a convenience class during the creation of a morphology.
    
    See also:
        :func:`~single_cell_parser.cell_parser.CellParser.determine_nseg` for determining the number of segments in a section, and API
        access to NEURON segments.
        
    See also:
        :class:`~singlecell_input_mapper.singlecell_input_mapper.reader._Edge` for a similar class 
        that is used in the :mod:`singlecell_input_mapper` reader.

    Attributes:
        label (str): label and ID of the segment (e.g. "Dendrite_1_0_0").
        hocLabel (str): Hoc label of the segment (e.g. "Soma", "Axon" ...).
        edgePts (list): List of points in the segment.
        diameterList (list): List of diameters at each point.
        parentID (int): label and ID of the parent segment.
        parentConnect (float): How far along the parent section the connection is (i.e. the `x`-coordinate).
        valid (bool): Flag indicating if the segment is valid.
    '''
    def __init__(self):
        self.label: str | None = None
        self.hocLabel: str | None = None
        self.edgePts: List[List[float]] | None = None
        self.diameterList: List[float] | None = None
        self.parentID: int | None = None
        self.parentConnect: float | None = None
        self.valid: bool | None = None


    def is_valid(self):
        """Check if this edge is valid.
        
        Edges are only valid if they have a :param:`label`, a :param:`hocLabel`, and at least one :param:`edgePts`.
        
        Returns:
            bool: True if the edge is valid, False otherwise.
        """
        if not self.label:
            self.valid = False
            return False
        if not self.hocLabel:
            self.valid = False
            return False
        if not len(self.edgePts):
            self.valid = False
            return False
        self.valid = True
        return True

    def __eq__(self, other):
        for attr, val in self.__dict__.items():
            if not val == getattr(other, attr): return False 
        for attr in other.__dict__:
            if attr not in self.__dict__: return False
        return True

