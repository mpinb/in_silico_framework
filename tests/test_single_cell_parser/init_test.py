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
            '86_CDK_20041214_BAC_run5_soma_Hay2013_C2center_apic_rec.param')
        self.network_param = os.path.join(
            TEST_DATA_FOLDER,
            'functional_constraints',
            'network.param')

        assert os.path.exists(self.cell_param)
        assert os.path.exists(self.network_param)

    def test_fast_and_slow_mode_of_build_parameters_gives_same_results(self):
        bp = scp.build_parameters
        comp = fancy_dict_compare(bp(self.cell_param, fast_but_security_risk = True), \
                                  bp(self.cell_param, fast_but_security_risk = False))
        assert comp == ''

        comp = fancy_dict_compare(bp(self.network_param, fast_but_security_risk = True), \
                                  bp(self.network_param, fast_but_security_risk = False))
        assert comp == ''

    def test_cell_modify_functions_in_neuron_param_is_respected(self):
        from mechanisms import l5pt as l5pt_mechanisms
        neuron_param = scp.build_parameters(getting_started.neuronParam)
        cell = scp.create_cell(neuron_param.neuron)
        diam_unscaled = next(
            s for s in cell.sections if s.label == 'ApicalDendrite').diam
        neuron_param.neuron['cell_modify_functions'] = scp.NTParameterSet(
            {'scale_apical': {
                'scale': 10
            }})
        cell = scp.create_cell(neuron_param.neuron)
        diam_scaled = next(
            s for s in cell.sections if s.label == 'ApicalDendrite').diam
        assert np.abs(diam_unscaled * 10 - diam_scaled) < 1e-4
