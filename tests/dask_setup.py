import os
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


def _launch_dask_cluster(config):
    ip = config.getoption("dask_server_ip")
    port = int(config.getoption("dask_server_port"))
    # Start a new Dask cluster
    cluster = LocalCluster(
        n_workers=DASK_N_WORKERS,
        threads_per_worker=DASK_TPW,
        memory_limit=DASK_MEM_LIMIT,
        dashboard_address=DASK_DASHBOARD_ADDRESS,
        ip=ip,
        scheduler_port=port,
    )
    client = Client(cluster)
    print(f"Started new Dask cluster at {ip}:{port}")
    return client, cluster
