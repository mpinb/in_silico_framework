import pytest, logging, socket, sys
from dask.distributed import LocalCluster, Client
logger = logging.getLogger("ISF").getChild(__name__)


def get_free_port():
    """Grab a free port from the OS for the scheduler."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def dask_cluster(pytestconfig):
    """Function-scoped Dask cluster isolated per test."""
    
    n_workers = int(pytestconfig.getini("DASK_N_WORKERS")) or 2
    mem_limit = pytestconfig.getini("DASK_MEM_LIMIT") or "2GB"
    scheduler_port = get_free_port()
    cluster = LocalCluster(
        n_workers = n_workers,
        threads_per_worker = 2,
        scheduler_port = scheduler_port,
        dashboard_address = None,  # Disable dashboard to avoid port clashes
        silence_logs = False,
        memory_limit = mem_limit,
    )
    yield cluster
    cluster.close()


@pytest.fixture(scope="function")
def client(dask_cluster, pytestconfig):
    n_workers = int(pytestconfig.getini("DASK_N_WORKERS")) or 2
    client = Client(dask_cluster)
    client.wait_for_workers(n_workers)
    client.forward_logging(logger)
    
    yield client
    # logs = client.get_worker_logs()
    client.close()
