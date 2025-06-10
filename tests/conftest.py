# Pytest configuration file
# this code will be run on each pytest worker before any other pytest code
# useful to setup whatever needs to be done before the actual testing or test discovery
# for setting environment variables, use pytest.ini or .env instead
import logging, os, pytest
from config.isf_logging import logger  # import from config to set handlers properly

# --- Import fixtures
from .fixtures.dataframe_fixtures import ddf, pdf
from .fixtures.dask_fixtures import client, dask_cluster
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
    parser.addini("DASK_N_WORKERS", "Number of Dask workers")
    parser.addini("DASK_MEM_LIMIT", "Memory limit for each Dask worker (e.g., '2GB')")


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

    
def _set_mpl_backend_non_gui():
    """
    Set matplotlib to use the agg backend
    """
    import matplotlib
    matplotlib.use("agg")
    import matplotlib.pyplot as plt
    plt.switch_backend("agg")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """
    pytest configuration
    """
    _setup_pytest_logging()
    import mechanisms.l5pt
    mechanisms.l5pt.load()   


def pytest_sessionstart(session):
    _set_mpl_backend_non_gui()
