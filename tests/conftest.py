# Pytest configuration file
# this code will be run on each pytest worker before any other pytest code
# useful to setup whatever needs to be done before the actual testing or test discovery
# for setting environment variables, use pytest.ini or .env instead
import logging, os, six,  pytest, time
from tests.dask_setup import _launch_dask_cluster, _write_cluster_logs
from dask.distributed import Client

# --- Import fixtures
from .fixtures.dataframe_fixtures import ddf, pdf
from .fixtures.dask_fixtures import client
from .context import TESTS_CWD
from mechanisms.l5pt import load_mechanisms
from .context import TESTS_CWD

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
DASK_N_WORKERS = 6
DASK_TPW = 1
DASK_MEM_LIMIT = "2GB"
DASK_DASHBOARD_ADDRESS = None

def pytest_runtest_teardown(item, nextitem):
    if "check_dask_health" in item.keywords:
        client = item.funcargs.get("client")
        if client is not None:
            try:
                # Run a lightweight task on the cluster to ensure it still works
                result = client.submit(lambda: 42).result(timeout=5)
                assert result == 42
            except Exception as e:
                pytest.fail(f"Dask client check failed: {e}")

    
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
    parser.addoption("--dask_server_ip", action="store", default="localhost")


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
    
    bc_downloaded = os.path.exists(os.path.join(os.path.dirname(TESTS_CWD), "barrel_cortex"))
    if path.fnmatch("*test_barrel_cortex*"):
        return not bc_downloaded  # skip if it is not downloaded


def _setup_logging():
    from config.isf_logging import logger as isf_logger

    # --------------- Setup logging output -------------------
    # only log warnings or worse
    isf_logger.setLevel(logging.WARNING)  # set logging level of ISF logger to WARNING
    # Suppress logs from verbose modules so they don't show in stdout
    isf_logger.addFilter(
        ModuleFilter(suppress_modules_list)
    )  # suppress logs from this module
    # redirect test ouput to log file with more verbose output
    if not os.path.exists(os.path.join(TESTS_CWD, "logs")):
        os.mkdir(os.path.join(TESTS_CWD, "logs"))
    isf_logging_file_handler = logging.FileHandler(
        os.path.join(TESTS_CWD, "logs", "test.log")
    )
    isf_logging_file_handler.setLevel(logging.INFO)
    isf_logger.addHandler(isf_logging_file_handler)

    
def _mpl_backend_agg():
    """
    Set matplotlib to use the agg backend
    """
    import matplotlib
    matplotlib.use("agg")
    import matplotlib.pyplot as plt
    plt.switch_backend("agg")


def _setup_dask(config):
    if os.getenv("PYTEST_XDIST_WORKER") is None:  # Only run in the main pytest process
        client, cluster = _launch_dask_cluster(
            config, 
            n_workers=DASK_N_WORKERS, 
            threads_per_worker=DASK_TPW, 
            mem_limit=DASK_MEM_LIMIT,
            dashboard_address=DASK_DASHBOARD_ADDRESS,
            )
        client.wait_for_workers(DASK_N_WORKERS)
        client.run(load_mechanisms)
        config.dask_cluster = cluster
        config.dask_client = client
    else:
        # Wait for scheduler to be available
        ip = config.getoption("dask_server_ip")
        port = int(config.getoption("dask_server_port"))
        address = f"{ip}:{port}"
        max_wait = 30  # seconds
        interval = 1
        start = time.time()
        while True:
            try:
                client = Client(address)
                break
            except (OSError, TimeoutError):
                if time.time() - start > max_wait:
                    raise RuntimeError(
                        f"Could not connect to Dask scheduler at {address} within {max_wait} seconds"
                    )
                time.sleep(interval)
        

@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """
    pytest configuration
    """
    import getting_started  # trigger creation of template files

    _mpl_backend_agg()
    _setup_logging()
    _setup_dask(config)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    """Clean up the Dask scheduler after pytest finishes."""
    if hasattr(config, "dask_client"):
        config.dask_client.close()
    if hasattr(config, "dask_cluster"):
        _write_cluster_logs(
            config.dask_cluster,
            os.path.join(TESTS_CWD, "logs", "dask_cluster.log"),
        )
        config.dask_cluster.close()