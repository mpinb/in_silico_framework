# Pytest configuration file
# this code will be run on each pytest worker before any other pytest code
# useful to setup whatever needs to be done before the actual testing or test discovery
# for setting environment variables, use pytest.ini or .env instead
import os, logging, socket, dask, six, sys
from Interface import logger as isf_logger
# --- Import fixtures
from .fixtures import client
from .fixtures.dataframe_fixtures import pdf, ddf
if six.PY3:  # pytest can be parallellized on py3: use unique ids for dbs
    from .fixtures.data_base_fixtures_py3 import (
        fresh_db,
        fresh_mdb,
        empty_db,
        empty_mdb,
        sqlite_db
    )
elif six.PY2:  # old pytest version needs explicit @pytest.yield_fixture markers. has been deprecated since 6.2.0
    from .fixtures.data_base_fixtures_py2 import (
        fresh_db,
        fresh_mdb,
        empty_db,
        empty_mdb,
        sqlite_db
    )
from .context import TEST_DATA_FOLDER, CURRENT_DIR

def import_worker_requirements():
    import compatibility
    import mechanisms

def ensure_workers_have_imported_requirements(client):
    """
    This function is called in the pytest_configure hook to ensure that all workers have imported the necessary modules
    """
    import sys
    def update_path(): sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    client.run(update_path)
    
    if six.PY3:
        # Add dask plugin in case workers get killed
        from distributed.diagnostics.plugin import WorkerPlugin
        class SetupWorker(WorkerPlugin):
            def __init__(self):
                import_worker_requirements()

            def setup(self, worker):
                """
                This gets called every time a new worker is added to the scheduler
                """
                import_worker_requirements()
        
        client.register_worker_plugin(SetupWorker())
    
    client.run(import_worker_requirements)

logger = logging.getLogger("ISF").getChild(__name__)
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
    parser.addoption("--dask_server_port", action="store", default="38786")


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def pytest_ignore_collect(path, config):
    if six.PY2:
        return (
            path.fnmatch("/*test_data_base/data_base/*")  # only run new DataBase tests on Py2
            or path.fnmatch("/*cell_morphology_visualizer_test*")  # don't run cmv tests on Py2
            )


def pytest_configure(config):
    """
    pytest configuration
    """
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

    c = distributed.Client(
        "localhost:" + str(config.getoption("--dask_server_port"))
        )
    ensure_workers_have_imported_requirements(c)
