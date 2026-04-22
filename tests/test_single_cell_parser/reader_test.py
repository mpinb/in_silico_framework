from __future__ import absolute_import
from single_cell_parser.io.morphology.hoc import read_hoc
from .context import this_folder
import os


def test_can_load_hoc_file_with_label_BasalDendrite():
    '''compare model infered from test data to expectancy'''
    path = os.path.join(this_folder, 'data', '85.hoc')
    #print path
    try:
        read_hoc(path)
        assert True
    except:
        assert False

def test_read_swc():
    pass
