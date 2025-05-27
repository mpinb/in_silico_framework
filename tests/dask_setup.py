from dask.distributed import LocalCluster, Client
import logging
logger = logging.getLogger("ISF").getChild(__name__)


def _launch_dask_cluster(
    config, 
    n_workers, 
    threads_per_worker, 
    mem_limit, 
    dashboard_address
    ):
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
        processes=True, 
    )
    client = Client(cluster)
    logger.info(f"Started new Dask cluster at {ip}:{port}")
    return client, cluster
