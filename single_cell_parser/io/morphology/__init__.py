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
Read, write and convert morphology files.

Specific readers for morphology files are defined in submodules.
This module specifies converters between :ref:`swc_file_format` and :ref:`hoc_file_format` morphologies.
"""
from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
from data_base.dbopen import dbopen
from config.isf_logging import get_isf_logger
from typing import Optional
from .hoc import read_hoc, write_hoc
from .swc import read_swc
from pathlib import Path

logger = get_isf_logger().getChild(__name__)

def read_morphology(fn):
    """Read a morphology in :ref:`hoc_file_format` or :ref:`swc_file_format` format.
    
    This function is a simply strategy pattern to decide which reader to use.

    Args:
        fn (str|:class:`~Path`): Name of the morphology file.

    Returns:
       List[_Edge]: List of :class:`~_Edge` objects for further parsing, usually by :meth:`~CellParser.spatialgraph_to_cell`

    Raises:
        NotImplementedError: If the given filename is not a :ref:`hoc_file_format` or :ref:`swc_file_format`
    """
    suffix = Path(fn).suffix
    if suffix.lower().endswith(".hoc"):
        return read_hoc(fn)
    elif suffix.lower() == ".swc":
        return read_swc(fn)
    else:
        raise NotImplementedError(f"No reader implemented for {suffix} files")

def convert_swc_to_hoc(
    swc_fn, 
    of,
    axon=False,
    ):
    """Convert a :ref:`swc_file_format` morphology file to :ref:`hoc_file_format` format.
    
    Args:
        swc_filepath (str): Path to the :ref:`swc_file_format` file to be converted.
        hoc_filepath (str): Output path for the :ref:`hoc_file_format` file.

    Raises:
        ValueError: If no soma points (type 1) are found in the SWC file.
    """
    from .swc import write_swc
    from single_cell_parser.cell_parser import CellParser
    cell_parser = CellParser(fn=swc_fn)
    cell_parser.spatialgraph_to_cell(
        axon=axon,
        force_connect_soma_halfway=False
        )
    write_hoc(
        sections=cell_parser.cell.sections, 
        of=of, 
    )

def convert_hoc_to_swc(
    hoc_fn, 
    of,
    axon=False,
    skip_myelin=False, 
    remap_sections=None
    ):
    """Convert a :ref:`hoc_file_format` morphology file to swc format.
    
    Args:
        hoc_fn (str): Path to the :ref:`hoc_file_format` morphology file.
        of (str): Output path for the resulting swc file.
        skip_myelin (bool):
            If True, myelin will not be written to the resulting .swc file.
        remap_sections (dict): 
            A dictionary mapping section indices to a custom label. 
            Custom labels
        axon (bool):
            Whether or not to include the axon in the resulting swc file.
            Default is `False``, because ISF by default ignores morphologically detailed axons in favor of a custom one 
            (see :meth:`~single_cell_parser.cell_parser.CellParser._create_ais_Hay2013`)

    Attention:
        The conversion from :ref:`hoc_file_format` to :ref:`swc_file_format` is slightly destructive.
        :ref:`hoc_file_format` allows you to specify connectivity between sections in terms of a continuous
        relative coordinate `x`. On the other hand, :ref:`swc_file_format` defines this based on a discrete point index.
        We make a best effort to choose the point closest to the `x` coordinate as specified in the :ref:`hoc_file_format`,
        but this is not guaranteed to exactly match the connection point.
        In reality, this is often only used for the soma, and ISF by default connects soma children at ``x=0.5`` anyways.

    Attention:
        When :param:`axon` is set to True, the axon is built  and written out according to :meth:`~single_cell_parser.cell_parser.CellParser._create_ais_Hay2013`,
        and has nothing to do with any axon that may be present in the :ref:`hoc_file_format` file.
    """
    from .swc import write_swc
    from single_cell_parser.cell_parser import CellParser
    cell_parser = CellParser(hoc_fn)
    cell_parser.spatialgraph_to_cell(
        axon=axon,
        force_connect_soma_halfway=False
        )
    write_swc(
        sections=cell_parser.cell.sections, 
        of=of, 
        skip_myelin=skip_myelin, 
        remap_sections=remap_sections
    )

