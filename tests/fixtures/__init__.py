import pytest, distributed, socket

@pytest.fixture(scope="session")
def client(pytestconfig):
    # Assume dask server and worker are already started
    # These are set up in the github workflow file.
    # If running tests locally, make sure you have a dask scheduler and dask worker running on the ports you want
    ip = pytestconfig.getoption("--dask_server_ip", default="localhost")
    c = distributed.Client(
        '{}:{}'.format(
            ip, 
            pytestconfig.getoption("--dask_server_port"))
        )
    return c
