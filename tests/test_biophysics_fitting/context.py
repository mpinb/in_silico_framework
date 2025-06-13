from __future__ import absolute_import
import os
import sys
from tests.context import TEST_DATA_FOLDER

PARENT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

sys.path.insert(0, PARENT)

cellParamName = os.path.join(
    TEST_DATA_FOLDER,
    'biophysical_constraints',
    '86_C2_center.param')