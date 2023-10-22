from __future__ import absolute_import
import os
import sys
import tempfile
import getting_started

parent = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, parent)

test_data_path = os.path.join(getting_started.parent, \
                              'example_simulation_data', \
                              'C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center/20150815-1530_20240')
assert os.path.exists(test_data_path)