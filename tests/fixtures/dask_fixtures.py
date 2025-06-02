import pytest, logging, socket, sys
from distributed.diagnostics.plugin import SchedulerPlugin
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
    try:
        from mechanisms.l5pt import load_mechanisms
        load_mechanisms()
    except Exception as e:
        print("Worker mechanism load error:", e, file=sys.stderr)
        raise


def safe_init_dask_workers(client, n_retries=3):
    workers = client.run_on_scheduler(lambda dask_scheduler: list(dask_scheduler.workers.keys()))
    for worker in workers:
        try:
            future = client.submit(init_dask_workers, workers=[worker])
            future.result()  # Wait for the result
            break  # Exit retry loop if successful
        except Exception as e:
            logger.error("Failed to initialize Dask worker after %d retries: %s", n_retries, e)
            raise e

            
class LoadMechanismsPlugin(SchedulerPlugin):
    def __init__(self):
      super().__init__()

    def add_worker(self, scheduler=None, worker=None, **kwargs):
        future = worker.submit(init_dask_workers)
        future.result()


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
    cluster.add_plugin(LoadMechanismsPlugin())
    client = Client(cluster)
    client.wait_for_workers(n_workers)
    safe_init_dask_workers(client)
    
    yield client
    client.close()
    cluster.close()
