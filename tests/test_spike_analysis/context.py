from __future__ import absolute_import
import os
import sys

this = os.path.dirname(__file__)
parent = os.path.abspath(os.path.dirname(this))
sys.path.insert(0, parent)

test_smr_path = os.path.join(
    this, 'WR69_Cell2_1338um_10ms100ms_AirPuff_Trial1_Data.smr')

assert os.path.exists(test_smr_path)