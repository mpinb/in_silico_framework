import pytest, os
from dask.distributed import LocalCluster, Client

DASK_N_WORKERS = 6
DASK_TPW = 1
DASK_MEM_LIMIT = "2GB"
DASK_DASHBOARD_ADDRESS = None


def _write_cluster_logs(cluster, log_file):
    logs = cluster.get_logs()
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    with open(log_file, "w", encoding="utf-8") as f:
        for address, log in logs.items():
            f.write(f"--- Logs from {address} ---\n")
            f.write(log + "\n\n")

@pytest.fixture(scope="session")
def dask_cluster():
    cluster = LocalCluster(
        n_workers=DASK_N_WORKERS,
        threads_per_worker=DASK_TPW,
        memory_limit=DASK_MEM_LIMIT,
        dashboard_address=DASK_DASHBOARD_ADDRESS,
    )
    yield cluster
    _write_cluster_logs(cluster, f"tests/logs/dask_combined_{os.environ.get("GITHUB_RUN_ID", "noid")}.log")
    cluster.close()

@pytest.fixture(scope="session")
def client(dask_cluster):
    client = Client(dask_cluster)
    yield client
    client.close()
