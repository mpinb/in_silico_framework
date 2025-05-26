import pytest, os, time, socket
from distributed.comm.core import CommClosedError
from dask.distributed import Client


@pytest.fixture(scope="session")
def client(pytestconfig):
    """Fixture to create a Dask client for the tests.
    
    This fixture requests the dask_cluster to ensure it is launched.
    For non-parent pytest workers, the `dask_scheduler` fixture will be None.
    For this reason, we simply use the pytest config to connect to the singular scheduler.
    """
    # Each pytest xdist worker will create its own Dask client
    # and connect to the same Dask cluster.
    # The tests should thus be thread-safe
    ip = pytestconfig.getoption("dask_server_ip")
    port = int(pytestconfig.getoption("dask_server_port"))
    address = f"{ip}:{port}"

    max_wait = 30  # seconds
    interval = 1
    start = time.time()

    while True:
        try:
            client = Client(address, timeout=max_wait)
            break
        except (OSError, TimeoutError, CommClosedError, socket.error):
            if time.time() - start > max_wait:
                raise RuntimeError(
                    f"Could not connect to Dask scheduler at {address} within {max_wait} seconds"
                )
            time.sleep(interval)

    yield client
    client.close()
