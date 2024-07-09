from __future__ import absolute_import
import os, sys, shutil, tempfile
import distributed
import pytest

parent = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, parent)
import distributed
from data_base import utils
import getting_started
from mechanisms import l5pt as l5pt_mechanisms
# set up paths
test_data_folder = os.path.join(
    getting_started.parent, 
    'example_data', 
    'simulation_data',
    'C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center/')
