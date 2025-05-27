import os, logging
from dask.distributed import LocalCluster, Client


def _write_cluster_logs(scheduler, log_file):
    logs = scheduler.get_logs()
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    with open(log_file, "w", encoding="utf-8") as f:
        for address, log in logs.items():
            f.write(f"--- Logs from {address} ---\n")
            f.write(log + "\n\n")

def _setup_dask_scheduler_logging(log_file):
    """Set up logging for the Dask cluster to write logs in real-time."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Create a file handler for logging
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # Create a formatter and attach it to the handler
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # Get the Dask logger and attach the handler
    dask_logger = logging.getLogger("distributed")
    dask_logger.setLevel(logging.INFO)
    dask_logger.addHandler(file_handler)

    # remove other handlers (e.g., console handlers) to avoid clutter
    for handler in dask_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            dask_logger.removeHandler(handler)

def _setup_dask_worker_logging(log_file):
    """Set up logging for a Dask worker to write logs in real-time."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Create a file handler for logging
    worker_name = os.environ.get("DASK_WORKER_NAME", "worker")
    worker_log_file = log_file.replace(".log", f"_{worker_name}.log")
    file_handler = logging.FileHandler(worker_log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # Create a formatter and attach it to the handler
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # Get the Dask worker logger and attach the handler
    worker_logger = logging.getLogger("distributed.worker")
    worker_logger.setLevel(logging.INFO)
    worker_logger.addHandler(file_handler)

    # remove other handlers (e.g., console handlers) to avoid clutter
    for handler in worker_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            worker_logger.removeHandler(handler)


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
        processes=False,  # Use threads instead of processes
    )
    client = Client(cluster)
    print(f"Started new Dask cluster at {ip}:{port}")
    return client, cluster
