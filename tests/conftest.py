# Pytest configuration file
# this code will be run before any other pytest code
# even before pytest discovery
# useful to setup whatever needs to be done before the actual testing or test discovery, such as the distributed.client_object_duck_typed
# for setting environment variables, use pytest.ini or .env instead
import os
import pytest
import socket
import Interface as I
from Interface import get_client, root_logger, root_logger_stream_handler
import logging
log = logging.getLogger(__name__)
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))

os.environ["IS_TESTING"] = "True"

suppress_modules_list = ["biophysics_fitting"]

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
            [module_name in m for module_name in self.suppress_modules_list]
            )

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

    output_thickness = os.path.join(CURRENT_DIR, 'test_dendrite_thickness', 'test_files', 'output')
    if not os.path.exists(output_thickness):
        os.mkdir(output_thickness)

    # Assume dask server and worker are already started
    # These are set up in the github workflow file.
    # If running locally, make sure you have a dask scheduler and dask worker running on these ports

    if six.PY2:
        client = distributed.Client('localhost:28786')
    else:
        client = distributed.Client('localhost:38786')
    log.info("setting distributed duck-typed object as module level attribute")
    distributed.client_object_duck_typed = client
    
    # Setup logging output
    # only log warnings
    root_logger.setLevel(logging.WARNING)  # set logging level of root logger to WARNING
    # Suppress logs from verbose modules so they don't show in stdout
    root_logger_stream_handler.addFilter(ModuleFilter(suppress_modules_list))  # suppress logs from this module
        