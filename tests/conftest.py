# Pytest configuration file
# this code will be run on each pytest worker before any other pytest code
# useful to setup whatever needs to be done before the actual testing or test discovery
# for setting environment variables, use pytest.ini or .env instead
import logging, os, pytest, time
from tests.dask_setup import _launch_dask_cluster 
from dask.distributed import Client
from distributed.comm.core import CommClosedError
from config.isf_logging import logger  # import from config to set handlers properly

# --- Import fixtures
from .fixtures.dataframe_fixtures import ddf, pdf
from .fixtures.dask_fixtures import client
from .context import TESTS_CWD
from .context import TESTS_CWD

# pytest can be parallellized on py3: use unique ids for dbs
from .fixtures.data_base_fixtures import (
    empty_db,
    fresh_db,
    sqlite_db,
)
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
    """Specify CLI args and pytest.ini options for Dask configuration.
    
    These are defined in pyproject.toml, although default values are repeated here.
    """
    parser.addoption("--dask_server_port", action="store", default="8786")
    parser.addoption("--dask_server_ip", action="store", default="localhost")
    parser.addini("DASK_N_WORKERS", "Number of Dask workers")
    parser.addini("DASK_TPW", "Threads per worker")
    parser.addini("DASK_MEM_LIMIT", "Memory limit per worker")
    parser.addini("DASK_DASHBOARD_ADDRESS", "Dashboard address")
    parser.addini("DASK_CLIENT_TIMEOUT", "Dask client-server timeout in seconds")
    parser.addini("DASK_WORKER_TIMEOUT", "Dask client-worker timeout in seconds")


def pytest_collection_modifyitems(session, config, items):
    """Custom hook to schedule heavy tests in pytest collection.
    
    Currently, heavy tests are simply scheduled first.
    This may be extended in the future.
    """
    heavy = []
    normal = []

    for item in items:
        if 'heavy' in item.keywords:
            heavy.append(item)
        else:
            normal.append(item)

    # Place heavy tests at the beginning
    items[:] = heavy + normal


def pytest_ignore_collect(collection_path, config):
    """If this evaluates to True, the test is ignored.

    Args:
        path (str): path to the test file
        config (Config): pytest config object
    """
    
    bc_downloaded = os.path.exists(os.path.join(os.path.dirname(TESTS_CWD), "barrel_cortex"))
    if collection_path.match("*test_barrel_cortex*"):
        return not bc_downloaded  # skip if it is not downloaded


def _is_pytest_mother_worker():
    return os.getenv("PYTEST_XDIST_WORKER") is None


def _setup_pytest_logging():

    # --------------- Setup logging output -------------------
    logger.setLevel(logging.WARNING)

    # Suppress logs from verbose modules so they don't show in stdout
    logger.addFilter(ModuleFilter(suppress_modules_list))

    # redirect test ouput to log file with more verbose output
    if not os.path.exists(os.path.join(TESTS_CWD, "logs")):
        os.mkdir(os.path.join(TESTS_CWD, "logs"))
    isf_logging_file_handler = logging.FileHandler(
        os.path.join(TESTS_CWD, "logs", "test.log")
    )

    # Remove the default console handler to avoid cluttering CI output
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            logger.removeHandler(handler)

    isf_logging_file_handler.setLevel(logging.INFO)
    logger.addHandler(isf_logging_file_handler)

    
def _mpl_backend_agg():
    """
    Set matplotlib to use the agg backend
    """
    import matplotlib
    matplotlib.use("agg")
    import matplotlib.pyplot as plt
    plt.switch_backend("agg")


def _setup_dask(config):
    """Setup the dask server and initialize dask workers.
    """
    from mechanisms.l5pt import load_mechanisms

    DASK_N_WORKERS = int(config.getini("DASK_N_WORKERS"))
    DASK_TPW = int(config.getini("DASK_TPW"))
    DASK_MEM_LIMIT = config.getini("DASK_MEM_LIMIT")
    DASK_DASHBOARD_ADDRESS = config.getini("DASK_DASHBOARD_ADDRESS")
    max_wait = config.getini("DASK_CLIENT_TIMEOUT")

    if _is_pytest_mother_worker():
        client, cluster = _launch_dask_cluster(
            config, 
            n_workers=DASK_N_WORKERS, 
            threads_per_worker=DASK_TPW, 
            mem_limit=DASK_MEM_LIMIT,
            dashboard_address=DASK_DASHBOARD_ADDRESS,
            )
        client.wait_for_workers(DASK_N_WORKERS)
        client.run(lambda: print("All workers connected."))
        client.run(load_mechanisms)
        client.run(_setup_pytest_logging)
    else:
        # Wait for scheduler to be available
        ip = config.getoption("dask_server_ip")
        port = int(config.getoption("dask_server_port"))
        address = f"{ip}:{port}"

        interval = 1
        start = time.time()
        while True:
            try:
                client = Client(address, timeout=max_wait)
                break
            except (OSError, TimeoutError, CommClosedError) as e:
                if time.time() - start > max_wait:
                    raise RuntimeError(
                        f"Could not connect to Dask scheduler at {address} within {max_wait} seconds"
                    )
                time.sleep(interval)
        

def _teardown_dask(config):
    if _is_pytest_mother_worker():
        ip = config.getoption("dask_server_ip")
        port = int(config.getoption("dask_server_port"))
        address = f"{ip}:{port}"
        client = Client(address)
        client.shutdown()

@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """
    pytest configuration
    """
    _setup_pytest_logging()


def pytest_sessionstart(session):
    import getting_started  # trigger creation of template files
    _mpl_backend_agg()
    config = session.config
    _setup_dask(config)  # Dask starts only when tests are about to run


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    """Clean up the Dask scheduler after pytest finishes."""
    _teardown_dask(config)