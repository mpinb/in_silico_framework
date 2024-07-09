from __future__ import absolute_import
import os
import sys
from getting_started import getting_started_dir

parent = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_FOLDER = os.path.join(
    getting_started_dir, 
    'example_data',
    )
TEST_SIMULATION_DATA_FOLDER = os.path.join(
    getting_started_dir, 
    'example_data',
    'simulation_data',
    'C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center')
assert os.path.exists(TEST_DATA_FOLDER)

sys.path.insert(0, parent)
