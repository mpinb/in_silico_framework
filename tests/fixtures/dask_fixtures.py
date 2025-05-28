import pytest, logging
from dask.distributed import LocalCluster, Client
from ..dask_setup import DASK_CLUSTER_PER_GW_WORKER, get_free_port
logger = logging.getLogger("ISF").getChild(__name__)


@pytest.fixture(scope="function")
def client(request):
    """Function-scoped Dask cluster isolated per test."""
    # Optional: use xdist worker id to offset port range
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "gw0")
    
    # Dynamically allocate ports for safety
    if worker_id not in DASK_CLUSTER_PER_GW_WORKER:
        scheduler_port = get_free_port()
        cluster = LocalCluster(
            n_workers=2,
            threads_per_worker=2,
            scheduler_port=scheduler_port,
            dashboard_address=None,  # Disable dashboard to avoid port clashes
            silence_logs=False,
        )
        client = Client(cluster)
        DASK_CLUSTER_PER_GW_WORKER[worker_id] = (cluster, client)
    
    cluster, client = DASK_CLUSTER_PER_GW_WORKER[worker_id]
    return client