import pytest, os, time, socket
from distributed.comm.core import CommClosedError
from tornado.iostream import StreamClosedError
from dask.distributed import Client


@pytest.fixture(scope="session")
def client(pytestconfig):
    """Fixture to create a Dask client for the tests.
    
    This fixture requests the dask_cluster to ensure it is launched.

    The dask client is evaluated lazily. This helps in race conditions where the client
    otherwise would try to connect before the Dask cluster is ready.
    """
    # Each pytest xdist worker will create its own Dask client
    # and connect to the same Dask cluster.
    # The tests should thus be thread-safe

    _client = None
    
    def get_client():
        nonlocal _client
        ip = pytestconfig.getoption("dask_server_ip")
        port = int(pytestconfig.getoption("dask_server_port"))
        address = f"{ip}:{port}"
        max_wait = pytestconfig.getini("DASK_CLIENT_TIMEOUT")
        last_exc = None
        interval = 2
        start = time.time()
        while True:
            try:
                _client = Client(address, timeout=10)
                break
            except (OSError, TimeoutError, StreamClosedError, CommClosedError) as e:
                last_exc = e
                if time.time() - start > max_wait:
                    raise RuntimeError(f"Could not connect to Dask scheduler at {address} within {max_wait} seconds") from last_exc
                time.sleep(interval)
        return _client

    yield get_client
    if _client:
        client.close()
