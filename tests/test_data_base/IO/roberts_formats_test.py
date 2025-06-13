from data_base.IO.roberts_formats import read_pandas_synapse_activation_from_roberts_format, write_pandas_synapse_activation_to_roberts_format
from tests.test_data_base import test_data_folder
from pandas.util.testing import assert_frame_equal
import os
from config import isf_is_using_mdb
if isf_is_using_mdb():
    sim_triail = "sim_trail_index"
else:
    sim_triail = "sim_trial_index"

def test_saved_and_reloaded_synapse_file_is_identical(tmpdir):
    synapse_file_path = os.path.join(
        test_data_folder, \
        '20150815-1530_20240', \
        'simulation_run0000_synapses.csv')
    assert os.path.exists(synapse_file_path)
    synapse_pdf = read_pandas_synapse_activation_from_roberts_format(\
                            synapse_file_path, **{sim_triail: 'asdasd'})

    try:
        path_file = os.path.join(tmpdir.dirname, 'test.csv')
        write_pandas_synapse_activation_to_roberts_format(
            path_file, synapse_pdf)
        synapse_pdf_reloaded = read_pandas_synapse_activation_from_roberts_format(
            path_file, 
            **{sim_triail: 'asdasd'})
    except:
        raise

    assert_frame_equal(
        synapse_pdf.dropna(axis=1, how='all'),
        synapse_pdf_reloaded.dropna(axis=1, how='all'))
