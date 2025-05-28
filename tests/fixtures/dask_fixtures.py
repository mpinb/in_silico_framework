import pytest, logging, socket
from dask.distributed import LocalCluster, Client
logger = logging.getLogger("ISF").getChild(__name__)


def get_free_port():
    """Grab a free port from the OS for the scheduler."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def init_dask_workers():
    """Initialize Dask worker with ISF mechanisms loaded.
    
    This is wrapped in a function to avoid recursion issues.
    Recursion issues may arise on windows because:

    - Windows spawns processes using spawn() instead of fork()
    - importing mechanisms.l5pt triggers load_mechanisms()
    - Pickling the load_mechanisms function subsequently leads to recursion issues 

    I don't fully understand why this happens, but wrapping it in a function seems to resolve the issue.

    - Bjorge 2025-05-28
    """
    from mechanisms.l5pt import load_mechanisms
    load_mechanisms()

@pytest.fixture(scope="function")
def client(pytestconfig):
    """Function-scoped Dask cluster isolated per test."""
    
    n_workers = int(pytestconfig.getini("DASK_N_WORKERS")) or 2
    # Dynamically allocate ports for safety
    scheduler_port = get_free_port()
    cluster = LocalCluster(
        n_workers = n_workers,
        threads_per_worker = 2,
        scheduler_port = scheduler_port,
        dashboard_address = None,  # Disable dashboard to avoid port clashes
        silence_logs = False,
    )
    client = Client(cluster)
    client.wait_for_workers(n_workers)
    # load mechanisms into NEURON namespace on whichever dask worker is assigned this test
    client.submit(init_dask_workers)
    
    yield client
    client.close()
    cluster.close()
