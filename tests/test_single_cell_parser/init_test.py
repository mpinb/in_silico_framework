from __future__ import absolute_import
import single_cell_parser as scp
import getting_started
from data_base.utils import fancy_dict_compare
import os
import pytest
from .context import *
from tests.context import TEST_DATA_FOLDER
import numpy as np


class TestSingleCellParserInit:

    def setup_class(self):
        self.cell_param = os.path.join(
            TEST_DATA_FOLDER,
            'biophysical_constraints',
            '86_C2_center.param')
        self.network_param = os.path.join(
            TEST_DATA_FOLDER,
            'functional_constraints',
            'network.param')

        assert os.path.exists(self.cell_param)
        assert os.path.exists(self.network_param)

    def test_cell_modify_functions_in_neuron_param_is_respected(self):
        from mechanisms import l5pt as l5pt_mechanisms
        neuron_param = scp.build_parameters(getting_started.neuronParam)
        
        # unscaled diameters
        neuron_param.neuron['cell_modify_functions'] = {}
        cell = scp.create_cell(neuron_param.neuron)
        diam_unscaled = next(
            s for s in cell.sections if s.label == 'ApicalDendrite').diam

        neuron_param.neuron['cell_modify_functions'] = scp.ParameterSet(
            {'scale_apical': {
                'scale': 10
            }})
        cell = scp.create_cell(neuron_param.neuron)
        diam_scaled = next(
            s for s in cell.sections if s.label == 'ApicalDendrite').diam
        assert np.abs(diam_unscaled * 10 - diam_scaled) < 1e-4
