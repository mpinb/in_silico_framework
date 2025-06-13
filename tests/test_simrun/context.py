from __future__ import absolute_import
import os
import sys
import tempfile
import getting_started

parent = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
data_dir = os.path.join(os.path.dirname(__file__), 'data')

sys.path.insert(0, parent)

from tests.context import TEST_DATA_FOLDER, TEST_SIMULATION_DATA_FOLDER

parent = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

cellParamName = os.path.join(
    TEST_DATA_FOLDER,
    'biophysical_constraints',
    '86_C2_center.param')
networkName = os.path.join(
    TEST_DATA_FOLDER,
    'functional_constraints', 
    'network.param')
example_path = os.path.join(
    TEST_SIMULATION_DATA_FOLDER, 
    '20150815-1530_20240', 
    'simulation_run0000_synapses.csv')