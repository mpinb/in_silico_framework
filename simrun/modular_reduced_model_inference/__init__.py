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

'''Create reduced models from synapse activation data.

This package implements strategies (see below) to create reduced models from synapse activation data.
It is implemented so that it allows for a "modular" inference: fitting can be performed in parallel on different parts of the data.
This was a necessary requirement when considering both the spatial and temporal dimension of the input snapse activation data.

A strategy defines a reduced model containing a set of free parameters :math:`\mathbf{x}` that are optimized to match the input data.
It also defines what data needs to be reproduced in the first place, and what constitutes a good match between the reduced model and the input data.
For a list of available strategies, see :py:mod:`~simrun.modular_reduced_model_inference.strategy`.

Example:
    :cite:t:`Bast_Fruengel_Kock_Oberlaender_2024` describes how to use a raised cosine basis
    to create a reduced model from synapse activation data.
    In this case, the input data are synapse activation patterns, and the target data are spike times.
    The strategy in this case is :py:class:`Strategy_spatiotemporalRaisedCosine`, which defines a linear sum
    of raised cosine basis functions. These functions are to be multiplied with the input data to predict spike probabilities.
    The free parameters are then the weights of the linear combination of these basis functions.
'''

from .data_extractor import (
    DataExtractor_categorizedTemporalSynapseActivation,
    DataExtractor_spatiotemporalSynapseActivation,
    DataExtractor_daskDataframeColumn,
    DataExtractor_ISI,
    DataExtractor_object,
    DataExtractor_spikeInInterval,
    DataExtractor_spiketimes
)

from .solver import (
    _Solver,
    Solver_COBYLA
)

from .reduced_model import (
    RaisedCosineBasis,
    Rm,
    DataView,
    DataSplitEvaluation,
    get_n_workers_per_ip    
)

from .strategy import (
    Strategy_categorizedTemporalRaisedCosine,
    Strategy_spatiotemporalRaisedCosine,
    Strategy_ISIcutoff,
    Strategy_ISIexponential,
    Strategy_ISIraisedCosine,
    Strategy_linearCombinationOfData,
    Strategy_temporalRaisedCosine_spatial_cutoff,
    CombineStrategies_sum,
    clear_memory,
    make_weakref,
    dereference,
    convert_to_numpy,
    _WEAKREF_ARRAY_LIST,
)