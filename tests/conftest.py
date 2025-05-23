# Pytest configuration file
# this code will be run on each pytest worker before any other pytest code
# useful to setup whatever needs to be done before the actual testing or test discovery
# for setting environment variables, use pytest.ini or .env instead
import logging, os, six, sys, pytest, time, psutil
from distributed.diagnostics.plugin import WorkerPlugin

# --- Import fixtures
from .fixtures import client
from .fixtures.dataframe_fixtures import ddf, pdf

if six.PY3:  
    # pytest can be parallellized on py3: use unique ids for dbs
    from .fixtures.data_base_fixtures_py3 import (
        empty_db,
        fresh_db,
        sqlite_db,
    )
elif six.PY2:  
    # old pytest version needs explicit @pytest.yield_fixture markers. has been deprecated since 6.2.0
    from .fixtures.data_base_fixtures_py2 import (
        fresh_db,
        empty_db,
        sqlite_db,
    )

from .context import CURRENT_DIR, TEST_DATA_FOLDER

def _import_worker_requirements():
    import compatibility
    from config.isf_logging import logger

def _setup_mpl_non_gui_backend():
    """
    Set up matplotlib to use a non-GUI backend.
    This is necessary for running tests in a headless environment (e.g., CI/CD pipelines).
    """
    import matplotlib
    matplotlib.use("Agg")

def pytest_runtest_teardown(item, nextitem):
    if "test_dask_health" in item.keywords:
        client = item.funcargs.get("client")
        if client is not None:
            try:
                # Run a lightweight task on the cluster to ensure it still works
                result = client.submit(lambda: 42).result(timeout=5)
                assert result == 42
            except Exception as e:
                pytest.fail(f"Dask client check failed: {e}")

def setup_dask_worker_context(client):
    """
    This function is called in the pytest_configure hook to ensure that all workers have imported the necessary modules
    """
    client.wait_for_workers(n_workers=len(client.ncores()))  # or just wait_for_workers(1)

    def update_path():
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    if six.PY3:
        class SetupWorker(WorkerPlugin):
            def setup(self, worker):
                _import_worker_requirements()
                _setup_mpl_non_gui_backend()
                update_path()

        client.register_worker_plugin(SetupWorker())
    
    
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
        return not any([module_name in m for module_name in self.suppress_modules_list])


def pytest_addoption(parser):
    parser.addoption("--dask_server_port", action="store", default="8786")
    parser.addoption(
        "--dask_server_ip", action="store", default="localhost"
    )  # default is localhost


def pytest_ignore_collect(path, config):
    """If this evaluates to True, the test is ignored.

    Args:
        path (str): path to the test file
        config (Config): pytest config object
    """
    if six.PY2:
        return path.fnmatch(
            "/*test_data_base/data_base/*"
        ) or path.fnmatch(  # only run new DataBase tests on Py3
            "/*cell_morphology_visualizer_test*"
        )  # don't run cmv tests on Py2
    
    bc_downloaded = os.path.exists(os.path.join(os.path.dirname(CURRENT_DIR), "barrel_cortex"))
    if path.fnmatch("*test_barrel_cortex*"):
        return not bc_downloaded  # skip if it is not downloaded


def pytest_configure(config):
    """
    pytest configuration
    """
    import matplotlib
    matplotlib.use("agg")
    import getting_started  # trigger creation of template files
    import mechanisms.l5pt  # trigger compilation if they don't exist yet
    import distributed
    import matplotlib.pyplot as plt
    plt.switch_backend("agg")
    from config.isf_logging import logger as isf_logger

    # --------------- Setup logging output -------------------
    # only log warnings or worse
    isf_logger.setLevel(logging.WARNING)  # set logging level of ISF logger to WARNING
    # Suppress logs from verbose modules so they don't show in stdout
    isf_logger.addFilter(
        ModuleFilter(suppress_modules_list)
    )  # suppress logs from this module
    # redirect test ouput to log file with more verbose output
    if not os.path.exists(os.path.join(CURRENT_DIR, "logs")):
        os.mkdir(os.path.join(CURRENT_DIR, "logs"))
    isf_logging_file_handler = logging.FileHandler(
        os.path.join(CURRENT_DIR, "logs", "test.log")
    )
    isf_logging_file_handler.setLevel(logging.INFO)
    isf_logger.addHandler(isf_logging_file_handler)

    # Wait until mechanisms are compiled
    while not mechanisms.l5pt.check_if_all_mechanisms_are_compiled():
        logger.info("Waiting for mechanisms to be compiled...")
        time.sleep(1)

    c = distributed.Client(
        "{}:{}".format(
            config.getoption("--dask_server_ip", default="localhost"),
            config.getoption("--dask_server_port"),
        )
    )

    setup_dask_worker_context(c)
