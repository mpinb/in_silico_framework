# Pytest configuration file
# this code will be run before any other pytest code
# even before pytest discovery
# useful to setup whatever needs to be done before the actual testing or test discovery, such as the distributed.client_object_duck_typed
# for setting environment variables, use pytest.ini or .env instead
import os, shutil, logging, socket, pytest, tempfile, distributed, model_data_base, dask, six, getting_started, Interface  # Interface just to check if setup works. is in essence already a test
from model_data_base.mdb_initializers.load_simrun_general import init
from model_data_base.utils import silence_stdout
import pandas as pd
import dask.dataframe as dd
from Interface import get_client
from Interface import logger as isf_logger
from Interface import logger_stream_handler as isf_logger_stream_handler
from model_data_base.IO.LoaderDumper import pandas_to_msgpack

logger = logging.getLogger("ISF").getChild(__name__)
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_FOLDER = os.path.join(getting_started.parent, \
                              'example_simulation_data', \
                              'C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center/')
os.environ["ISF_IS_TESTING"] = "True"

suppress_modules_list = ["biophysics_fitting", "distributed"]


class ModuleFilter(logging.Filter):
    """
    Given an array of module names, suppress logs from those modules

    Args:
        suppress_modules_list (array): array of module names
    """

    def __init__(self, suppress_modules_list):
        self.suppress_modules_list = suppress_modules_list

    def filter(self, record):
        m = record.getMessage()
        return not any(
            [module_name in m for module_name in self.suppress_modules_list])


def pytest_addoption(parser):
    parser.addoption("--dask_server_port", action="store", default="38787")


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def pytest_configure(config):
    import distributed
    import matplotlib
    import six
    matplotlib.use('agg')
    import matplotlib.pyplot as plt
    plt.switch_backend('agg')

    output_thickness = os.path.join(CURRENT_DIR, 'test_dendrite_thickness',
                                    'test_files', 'output')
    if not os.path.exists(output_thickness):
        os.mkdir(output_thickness)

    # --------------- Setup logging output -------------------
    # only log warnings or worse
    isf_logger.setLevel(
        logging.WARNING)  # set logging level of ISF logger to WARNING
    # Suppress logs from verbose modules so they don't show in stdout
    isf_logger.addFilter(
        ModuleFilter(suppress_modules_list))  # suppress logs from this module
    # redirect test ouput to log file with more verbose output
    if not os.path.exists(os.path.join(CURRENT_DIR, "logs")):
        os.mkdir(os.path.join(CURRENT_DIR, "logs"))
    isf_logging_file_handler = logging.FileHandler(
        os.path.join(CURRENT_DIR, "logs", "test.log"))
    isf_logging_file_handler.setLevel(logging.INFO)
    isf_logger.addHandler(isf_logging_file_handler)

    # --------------- Setup dask  -------------------

    dask_config = {
        "worker": {  # set worker config
            "memory_target": 0.90,
            "memory_spill": False,
            "memory_pause": False,
            "memory_terminate": False,
            },
        }
    dask.config.set(dask_config)


@pytest.fixture
def client(pytestconfig):
    # Assume dask server and worker are already started
    # These are set up in the github workflow file.
    # If running tests locally, make sure you have a dask scheduler and dask worker running on the ports you want
    return distributed.Client('localhost:{}'.format(
        pytestconfig.getoption("--dask_server_port")))

@pytest.fixture
def pdf():
    """Returns a pandas DataFrame with various types. No column has mixed value types though.

    Returns:
        pd.DataFrame: A dataframe
    """
    return pd.DataFrame({0: [1,2,3,4,5,6], 1: ['1', '2', '3', '1', '2', '3'], '2': [False, True, True, False, True, False], \
                                 'myname': ['bla', 'bla', 'bla', 'bla', 'bla', 'bla']})

@pytest.fixture
def ddf(pdf):
    ddf = dd.from_pandas(pdf, npartitions=2)
    return ddf

if six.PY3:  # pytest can be parallellized on py3: use unique ids for mdbs

    @pytest.fixture
    def fresh_mdb(worker_id):
        """Pytest fixture for a ModelDataBase object with a unique temp path.
        Initializes data with model_data_base.mdb_initializers.load_simrun_general.init
        Contains 8 keys with data:
        1. simresult_path
        2. filelist
        3. sim_trail_index
        4. metadata
        5. voltage_traces
        6. synapse_activation
        7. cell_activation
        8. spike_times

        Yields:
            model_data_base.ModelDataBase: An mdb with data
        """
        # unique temp path
        path = tempfile.mkdtemp(prefix=worker_id)
        mdb = model_data_base.ModelDataBase(path)
        #self.mdb.settings.show_computation_progress = False

        with silence_stdout:
            init(mdb,
                 TEST_DATA_FOLDER,
                 rewrite_in_optimized_format=False,
                 parameterfiles=False,
                 dendritic_voltage_traces=False)

        yield mdb
        # cleanup
        for key in mdb.keys():
            del key
        del mdb
        shutil.rmtree(path)

    @pytest.fixture
    def empty_mdb(worker_id):
        """Pytest fixture for a ModelDataBase object with a unique temp path.
        Does not initialize data, in contrast to fresh_mdb

        Yields:
            model_data_base.ModelDataBase: An empty mdb
        """
        # unique temp path
        path = tempfile.mkdtemp(prefix=worker_id)
        mdb = model_data_base.ModelDataBase(path)

        yield mdb
        # cleanup
        for key in mdb.keys():
            del key
        del mdb
        shutil.rmtree(path)

    @pytest.fixture
    def sqlite_db():
        from model_data_base.sqlite_backend.sqlite_backend import SQLiteBackend as SqliteDict
        tempdir = tempfile.mkdtemp()
        path = os.path.join(tempdir, 'tuplecloudsql_test.db')
        db = SqliteDict(path)

        yield db
        # cleanup
        if os.path.exists(tempdir):
            shutil.rmtree(tempdir)

elif six.PY2:  # old pytest version needs explicit @pytest.yield_fixture markers. has been deprecated since 6.2.0

    # Py2 needs msgpack dumper, as parquet was not yet implemented for pandas DataFrames
    @pytest.yield_fixture
    def fresh_mdb():
        """Pytest fixture for a ModelDataBase object with a unique temp path.
        Initializes data with model_data_base.mdb_initializers.load_simrun_general.init
        Contains 8 keys with data:
        1. simresult_path
        2. filelist
        3. sim_trail_index
        4. metadata
        5. voltage_traces
        6. synapse_activation
        7. cell_activation
        8. spike_times

        Yields:
            model_data_base.ModelDataBase: An mdb with data
        """
        # unique temp path
        path = tempfile.mkdtemp()
        mdb = model_data_base.ModelDataBase(path)
        #self.mdb.settings.show_computation_progress = False

        with silence_stdout:
            init(mdb,
                 TEST_DATA_FOLDER,
                 rewrite_in_optimized_format=False,
                 parameterfiles=False,
                 dendritic_voltage_traces=False,
                 dumper=pandas_to_msgpack)  # no Parquet dumper

        yield mdb
        # cleanup
        for key in mdb.keys():
            del key
        del mdb
        shutil.rmtree(path)

    @pytest.yield_fixture
    def empty_mdb():
        """Pytest fixture for a ModelDataBase object with a unique temp path.
        Does not initialize data, in contrast to fresh_mdb

        Yields:
            model_data_base.ModelDataBase: An empty mdb
        """
        # unique temp path
        path = tempfile.mkdtemp()
        mdb = model_data_base.ModelDataBase(path)

        yield mdb
        # cleanup
        for key in mdb.keys():
            del key
        del mdb
        shutil.rmtree(path)

    @pytest.yield_fixture
    def sqlite_db():
        from model_data_base.sqlite_backend.sqlite_backend import SQLiteBackend as SqliteDict
        tempdir = tempfile.mkdtemp()
        path = os.path.join(tempdir, 'tuplecloudsql_test.db')
        db = SqliteDict(path)

        yield db
        # cleanup
        if os.path.exists(tempdir):
            shutil.rmtree(tempdir)
