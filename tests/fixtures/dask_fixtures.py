import pytest, logging, socket
from dask.distributed import LocalCluster, Client
logger = logging.getLogger("ISF").getChild(__name__)


def get_free_port():
    """Grab a free port from the OS for the scheduler."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


@pytest.fixture(scope="function")
def client(pytestconfig):
    """Function-scoped Dask cluster isolated per test."""
    # Optional: use xdist worker id to offset port range
    # worker_id = getattr(request.config, "workerinput", {}).get("workerid", "gw0")
    
    # Dynamically allocate ports for safety
    scheduler_port = get_free_port()
    cluster = LocalCluster(
        n_workers = 2,
        threads_per_worker = 2,
        scheduler_port = scheduler_port,
        dashboard_address = None,  # Disable dashboard to avoid port clashes
        silence_logs = False,
        mem_limit = pytestconfig.getini("DASK_MEM_LIMIT") or "2GB",
        threads_per_worker = pytestconfig.getini("DASK_TPW") or 1,
    )
    client = Client(cluster)
    
    yield client
    client.close()
    cluster.close()