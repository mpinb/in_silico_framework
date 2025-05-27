import pytest
import logging
logger = logging.getLogger("ISF").getChild(__name__)

@pytest.fixture(scope="function")
def client(pytestconfig):
    """Fixture to create a Dask client for the tests.
    """
    from dask.distributed import Client
    # Each pytest xdist worker will create its own Dask client
    # and connect to the same Dask cluster.
    # The tests should thus be thread-safe
    ip = pytestconfig.getoption("dask_server_ip")
    port = int(pytestconfig.getoption("dask_server_port"))
    address = f"{ip}:{port}"
    max_server_wait = pytestconfig.getini("DASK_CLIENT_TIMEOUT")
    max_worker_wait = pytestconfig.getini("DASK_WORKER_TIMEOUT")
    client = Client(
        address, 
        timeout=max_server_wait,
    )

    yield client
    logger.info(f"Active workers: {list(client._scheduler_identity.workers)}")
    # client.close()