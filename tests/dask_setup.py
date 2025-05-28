import logging, socket
logger = logging.getLogger("ISF").getChild(__name__)

# Registry to store clusters per worker
DASK_CLUSTER_PER_GW_WORKER = {}


def get_free_port():
    """Grab a free port from the OS for the scheduler."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]