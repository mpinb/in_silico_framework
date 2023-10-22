import tempfile
import warnings
from ..context import *
from model_data_base.mdb_initializers.load_simrun_general \
            import optimize as optimize_simrun_general
from model_data_base.mdb_initializers.synapse_activation_binning \
            import init as init_synapse_activation

from model_data_base.IO.LoaderDumper import dask_to_csv, dask_to_msgpack, dask_to_categorized_msgpack
from model_data_base.utils import silence_stdout
import distributed

optimize_simrun_general = silence_stdout(optimize_simrun_general)


def test_API(fresh_mdb, client):
    optimize_simrun_general(fresh_mdb, client=client)
    init_synapse_activation(fresh_mdb, groupby='EI')
    init_synapse_activation(fresh_mdb, groupby=['EI'])
    init_synapse_activation(fresh_mdb, groupby=['EI', 'proximal'])
