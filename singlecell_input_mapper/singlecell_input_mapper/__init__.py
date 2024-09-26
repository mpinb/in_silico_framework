"""
Calculate the connectivity of individual neuron morphologies.
Based on methods and data presented in :cite:t:`Egger_Dercksen_Udvary_Hege_Oberlaender_2014` and :cite:t:`Udvary_Harth_Macke_Hege_De_Kock_Sakmann_Oberlaender_2022`.

This package contains methods to create anatomical realizations for the connectivity of single neurons.
To create anatomical realizations, it is recommended to use the high-level
pipeline :py:meth:`~singlecell_input_mapper.map_singlecell_inputs.map_singlecell_inputs`, which call supon various methods and classes presented in this package.

Inputs:

- The morphology and location of the postsynaptic neuron
- number of cells per cell type, per anatomical area.
- The 3D density of post-synaptic targets (PSTs) in the neuropil (cell type unspecific)
- The 3D density of boutons in the neuropil (cell type specific)
- The 1D and 2D densities of PSTs onto the postsynaptic neuron per length and area (cell type specific)

Attention:
    This package has similar, but not identical functionality as :py:mod:`single_cell_parser`. 
    :py:mod:`single_cell_parser` is specialized to handle biophysical and electrical properties,
    while this package is specialized to handle morphological and connectivity attributes of single cells. 
    
    It is unlikely to confuse the two in practice; the classes and methods here are used by the pipeline method
    :py:mod:`singlecell_input_mapper.map_singlecell_inputs`, and rarely directly invoked or imported.
    In addition, the pipeline of creating anatomical realizations is very distinct from the pipeline of 
    creating biophysical models, and crossover between the two pipelines is unlikely. 
    Nonetheless, beware of the following classes and methods that are duplicates only in name:
    
    .. list-table:: 
        :header-rows: 1

        * - :py:mod:`singlecell_input_mapper.singlecell_input_mapper`
          - :py:mod:`single_cell_parser`
        * - :class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell`
          - :class:`~single_cell_parser.cell.Cell`
        * - :class:`~singlecell_input_mapper.singlecell_input_mapper.cell.CellParser`
          - :class:`~single_cell_parser.cell_parser.CellParser`
        * - :class:`~singlecell_input_mapper.singlecell_input_mapper.reader.Edge`
          - :class:`~single_cell_parser.reader.Edge`
        * - :class:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseMapper`
          - :class:`~single_cell_parser.synapse_mapper.SynapseMapper`
        * - :class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`
          - :class:`~single_cell_parser.scalar_field.ScalarField`
        * - :py:class:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper`
          - :py:class:`~single_cell_parser.network.NetworkMapper`
        * - :py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Synapse`
          - :py:class:`~single_cell_parser.synapse.Synapse`
        * - :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.reader.read_hoc_file`
          - :py:meth:`~single_cell_parser.reader.read_hoc_file`
        * - :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.reader.read_scalar_field`
          - :py:meth:`~single_cell_parser.reader.read_scalar_field`

Author:
 
    Robert Egger
    Computational Neuroanatomy
    Max Planck Institute for Biological Cybernetics
    Tuebingen, Germany
"""

from __future__ import absolute_import
from .reader import *
from .writer import *
from .network_embedding import *
from .synapse_mapper import *
from .scalar_field import *
from .cell import CellParser

#===============================================================================
# for testing only
#===============================================================================
#from writer import *
#from cell import *
#from synapse_mapper import *