from __future__ import absolute_import
import os
import numpy as np
import neuron

h = neuron.h
import single_cell_parser as scp
import pickle
from getting_started import getting_started_dir  # path to getting started folder
from single_cell_parser.serialize_cell import *
from data_base.utils import silence_stdout
import mechanisms.l5pt
from tests.context import TEST_DATA_FOLDER


class TestSerializeCell:

    def setup_class(self):
        cell_param = os.path.join(
            TEST_DATA_FOLDER,
            'biophysical_constraints',
            '86_C2_center.param')
        cell_param = scp.build_parameters(
            cell_param)  # this is the main method to load in parameterfiles
        # load scaled hoc morphology
        cell_param.neuron.filename = os.path.join(
            TEST_DATA_FOLDER,
            'anatomical_constraints',
            '86_C2_center_scaled_diameters.hoc')
        with silence_stdout:
            cell = scp.create_cell(cell_param.neuron)

        iclamp = h.IClamp(0.5, sec=cell.soma)
        iclamp.delay = 150  # give the cell time to reach steady state
        iclamp.dur = 5  # 5ms rectangular pulse
        iclamp.amp = 1.9  # 1.9 ?? todo ampere
        scp.init_neuron_run(cell_param.sim, vardt=True)  # run the simulation

        self.cell = cell

    def test_can_be_pickled(self):
        silent = cell_to_serializable_object(self.cell)
        pickle.dumps(silent)

    def test_values_are_the_same_after_reload(self):
        silent = cell_to_serializable_object(self.cell)
        cell2 = restore_cell_from_serializable_object(silent)

        np.testing.assert_array_equal(np.array(self.cell.tVec), cell2.tVec)
        np.testing.assert_array_equal(np.array(self.cell.soma.recVList[0]), \
                                      cell2.soma.recVList[0])
