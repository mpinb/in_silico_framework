import os
from dask.distributed import LocalCluster, Client




def _write_cluster_logs(cluster, log_file):
    logs = cluster.get_logs()
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    with open(log_file, "w", encoding="utf-8") as f:
        for address, log in logs.items():
            f.write(f"--- Logs from {address} ---\n")
            f.write(log + "\n\n")


def _launch_dask_cluster(config, n_workers, threads_per_worker, mem_limit, dashboard_address):
    ip = config.getoption("dask_server_ip")
    port = int(config.getoption("dask_server_port"))
    # Start a new Dask cluster
    cluster = LocalCluster(
        n_workers=n_workers,
        threads_per_worker=threads_per_worker,
        memory_limit=mem_limit,
        dashboard_address=dashboard_address,
        ip=ip,
        scheduler_port=port,
    )
    client = Client(cluster)
    print(f"Started new Dask cluster at {ip}:{port}")
    return client, cluster
