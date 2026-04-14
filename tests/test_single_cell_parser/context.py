from __future__ import absolute_import
import os
import sys
import neuron
from tests.context import TEST_DATA_FOLDER

h = neuron.h

parent = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
this_folder = os.path.abspath(os.path.dirname(__file__))
fname = os.path.join(this_folder, 'data', '85.hoc')
sys.path.insert(0, parent)


HOC_FN = os.path.join(
    TEST_DATA_FOLDER,
    'anatomical_constraints', 
    '86_C2_center_scaled_diameters.hoc')
SWC_FN = os.path.join(
    TEST_DATA_FOLDER,
    'anatomical_constraints', 
    '86_C2_center_scaled_diameters.swc')

NEUP_FN = os.path.join(
    TEST_DATA_FOLDER,
    'biophysical_constraints', 
    '86_C2_center.param')