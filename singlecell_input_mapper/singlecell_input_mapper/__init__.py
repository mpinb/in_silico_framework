"""
Tool for calculating the connectivity of individual neuron morphologies.
Based on methods and data presented in :cite:`Egger_Dercksen_Udvary_Hege_Oberlaender_2014`.

This package contains methods to create mutliple anatomical realizations for the connectivity of single neurons.

Inputs:

- single neuron morphology
- 3D PST densities for normalization of innervation calculations
- number of cells per cell type, per anatomical area.
- PST length/area constants of the postsynaptic neuron.
- presynaptic bouton densities of individual axon morphologies, sorted by presynaptic column and cell type

Pipeline:

1. The bouton density field is a scalar field with defined voxel resolution. This voxel resolution
can reflect e.g. biological variability form animal to animal (as is the case for which this package was developed),
or measurement error.
2. Calculate the overlap between these voxels and the dendrites of the postsynaptic neuron morphology using Liang-Barsky clipping :cite:`liang1984new`.
3. Calculate a synapse density field by multiplying the bouton density field with PST density field at these voxels.
4. Normalize the density field using cell-type specific PST length/area constraints and the number of cells per cell type.
5. Poisson sample synapses from this density field and randomly assign them to the dendritic branch in that voxel.

Generating synapses from density fields yields an anatomical connectivity model, which is referred to as
a "realization" of the anatomical connectivity. 
Density meshes are accessed using :class:`scalar_field.ScalarField`.
:class:`synapse_mapper.SynapseMapper` makes use of :class:`synapse_mapper.SynapseDensity` for steps 2 to 4,
and finalizes step 5 by itself.

Outputs:

- Summary files containing information about number and presynaptic type and column of anatomical synapses
- AmiraMesh landmark file containing 3D synapse locations of anatomical synapses of each presynaptic type and column
- Synapse location and connectivity file compatible with :py:mod:`simrun`.

Warning:
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
        * - :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.cell.Synapse`
          - :py:meth:`~single_cell_parser.synapse.Synapse`
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