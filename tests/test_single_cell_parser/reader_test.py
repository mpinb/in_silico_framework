from __future__ import absolute_import
from single_cell_parser.reader import read_hoc_file
from .context import *


def test_can_load_hoc_file_with_label_BasalDendrite():
    '''compare model infered from test data to expectancy'''
    path = os.path.join(this_folder, 'data', '85.hoc')
    #print path
    try:
        read_hoc_file(path)
        assert True
    except:
        assert False
