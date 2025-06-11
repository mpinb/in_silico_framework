from __future__ import absolute_import
import os
import sys
import tempfile
import getting_started

parent = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
data_dir = os.path.join(os.path.dirname(__file__), 'data')

sys.path.insert(0, parent)

from tests.context import (
    TEST_DATA_FOLDER, 
    TEST_SIMULATION_DATA_FOLDER, 
    TEST_SIMULATION_DATA_SUBSAMPLED_FOLDER
    )

parent = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

NEUP_FN = os.path.join(
    TEST_DATA_FOLDER,
    'biophysical_constraints',
    '86_C2_center.param')
NETP_FN = os.path.join(
    TEST_DATA_FOLDER,
    'functional_constraints', 
    'network.param')
SYN_ACT_FN = os.path.join(
    TEST_SIMULATION_DATA_FOLDER, 
    'simulation_run0000_synapses.csv')
SYN_ACT_SUBSAMPLED_FN = os.path.join(
    TEST_SIMULATION_DATA_SUBSAMPLED_FOLDER, 
    'simulation_run0000_synapses.csv')