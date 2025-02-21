"""
Configuration for locking servers

Checks the environment variable ``ISF_DISTRIBUTED_LOCK_CONFIG`` for a path to a ``.yml`` file providing file locking configuration.
The following locking servers/types are supported:

.. list-table::
   :header-rows: 1

   * - Locking Server
     - Description
     - Documentation
   * - Redis
     - In-memory data structure store used as a database, cache, and message broker.
     - `Redis Documentation <https://redis-py.readthedocs.io/en/stable/>`_
   * - Zookeeper
     - Centralized service for maintaining configuration information, naming, providing distributed synchronization, and providing group services.
     - `Zookeeper Documentation <https://kazoo.readthedocs.io/en/latest/index.html>`_
   * - File
     - Fasteners file-based locking.
     - :py:class:`~data_base.distributed_lock.InterProcessLockNoWritePermission` and `Fasteners Documentation <https://fasteners.readthedocs.io/en/latest/>`_


If no such file exists, or the environment variable is not set, a default configuration is used, which uses (in order of decreasing precedence):

1. A redis server running on ``spock`` at port ``8885``
2. A redis server running on ``localhost`` at port ``6379``
3. File-based locking.

Example::

    >>> os.environ["ISF_DISTRIBUTED_LOCK_CONFIG"] = config_path
    >>> with open(config_path, "r" ) as f:
    ...     config = yaml.load(f, Loader=YamlLoader)
    >>> config
    [{'type': 'zookeeper', 'config': {'hosts':'localhost', 'port': 8885'}}]
    # or
    >>> DEFUALT_CONFIG
    [{'type': 'redis', 'config': {'host': 'spock', 'port': 8885, 'socket_timeout': 1}},
    {'type': 'redis', 'config': {'host': 'localhost', 'port': 6379, 'socket_timeout': 1}},
    {'type': 'file'}]

"""

# import fasteners
# import redis
import yaml
import os
from compatibility import YamlLoader
from config.isf_logging import logger as isf_logger

logger = isf_logger.getChild(__name__)

# Lazy initialization of the locking server and client
# These globals are set only when they're needed.
_SERVER = None
_CLIENT = None
_CONFIG = None
DEFAULT_CONFIG = [
    dict(type="redis", config=dict(host="spock", port=8885, socket_timeout=1)),
    dict(type="redis", config=dict(host="localhost", port=6379, socket_timeout=1)),
    dict(type="file"),
]

def _get_locking_config():
    """Get the locking configuration from the environment variable ``ISF_DISTRIBUTED_LOCK_CONFIG``.
    
    This method allows for a lazy evaluation of the locking configuration, 
    and is used to set the global variable ``_CONFIG``.
    """
    global _CONFIG

    # locking config is already set: return it
    if _CONFIG is not None:
        config = _CONFIG
    
    # check if locking is blocked
    elif "ISF_DISTRIBUTED_LOCK_BLOCK" in os.environ:
        config = None
    
    # check if locking config is set in the env variables
    elif "ISF_DISTRIBUTED_LOCK_CONFIG" in os.environ:
        config_path = os.environ["ISF_DISTRIBUTED_LOCK_CONFIG"]
        with open(config_path, "r") as f:
            config = yaml.load(f, Loader=YamlLoader)

    # use default config
    else:
        logger.attention(
            "Environment variable ISF_DISTRIBUTED_LOCK_CONFIG is not set. "
            + "Falling back to default configuration."
        )
        config = DEFAULT_CONFIG
    _CONFIG = config
    return config


def _get_locking_server_client_from_config():
    locking_config = _get_locking_config()
    for server in locking_config:
        logger.info(
            "Trying to connect to distributed locking server {}".format(str(server))
        )
        if server["type"] == "redis":
            import redis
            try:
                c = redis.StrictRedis(**server["config"])
                c.client_list()
                logger.info("success!")
                client = c
            except (redis.exceptions.TimeoutError, redis.exceptions.ConnectionError) as e:
                logger.error(e)
        elif server["type"] == "file":
            logger.warning(
                "Using file based locking. "
                "Please be careful on nfs mounts as file based locking has issues in this case."
            )
            client = None
        elif server["type"] == "zookeeper":
            import kazoo.client
            try:
                zk = kazoo.client.KazooClient(**server["config"])
                zk.start()
                logger.info("success!")
                client = zk
            except Exception as e:
                logger.error(e)
        else:
            raise NotImplementedError()
    return server, client


def get_locking_server_client():
    """Get the file locking client object, depending on the file locking configuration.

    File locking configuration should be set by the environment variable ``ISF_DISTRIBUTED_LOCK_CONFIG``, pointing to a path to
    a ``.yml`` file providing file locking configuration.

    See also:
        :py:mod:`data_base.distributed_lock` for more info on the file locking configuration.
    """
    global _SERVER
    global _CLIENT

    if "ISF_DISTRIBUTED_LOCK_BLOCK" in os.environ:
        return None, None
    
    if _SERVER is None:
        _SERVER, _CLIENT = _get_locking_server_client_from_config()
    
    return _SERVER, _CLIENT
    

def get_locking_client():
    """Get the locking client"""
    global _CLIENT
    if _CLIENT is None:
        _SERVER, _CLIENT = get_locking_server_client()
    return _CLIENT

def get_locking_server():
    """Get the locking server"""
    global _SERVER
    if _SERVER is None:
        _SERVER, _CLIENT = get_locking_server_client()
    return _SERVER


def update_config(c):
    """
    Update the global configuration variables with the provided configuration.

    Args:
        c (dict): A dictionary containing the new configuration values.

    Returns:
        None
    """
    global _CONFIG
    global _SERVER
    global _CLIENT
    _CONFIG = c
    _SERVER, _CLIENT = _get_locking_server_client_from_config()


class InterProcessLockNoWritePermission:
    """Check if the target file or directory has write access, and only lock it if so.

    If the user has write permissions to the path, then locking is necessary. Otherwise not, and lock acquire returns True without a lock

    Args:
        path (str): path to check.

    See also:
        [Fasteners InterProcessLock](https://fasteners.readthedocs.io/en/latest/guide/inter_process/)

    Attributes:
        lock (:py:class:`~fasteners.InterProcessLock` or None): The lock object if the user has write permissions, None otherwise.
    """

    def __init__(self, path):
        """

        Args:
            path (str): path to check."""
        if os.access(path, os.W_OK):
            import fasteners

            self.lock = fasteners.InterProcessLock(path)
        else:
            self.lock = None

    def acquire(self):
        """Acquire the lock on a path if the user has write permissions.

        If the user has no write permissions, then no lock is set and ``True`` is returned.

        Returns:
            bool: True if the lock was acquired successfully or if locking is not necessary, False otherwise.
        """
        if self.lock:
            return self.lock.acquire()
        return True

    def release(self):
        """Release the lock on a path if it was acquired.

        Returns:
            None
        """
        if self.lock:
            self.lock.release()


def get_lock(name):
    """Fetch the correct lock, depending on global locking server configuration.

    Reads the locking configuration from the global variable ``SERVER`` and infers the correct lock type.
    The following locks are supported:

    - :py:class:`~data_base.distributed_lock.InterProcessLockNoWritePermission`: for file based locking.
    - :py:class:`redis.lock.Lock`: for redis based locking.
    - :py:class:`kazoo.client.Lock`: for Apache zookeeper based locking.

    See also:
        `Kazoo documentation <https://kazoo.readthedocs.io/en/latest/index.html>`_ and
        `Redis documentation <https://redis-py.readthedocs.io/en/stable/>`_
    """
    if "ISF_DISTRIBUTED_LOCK_BLOCK" in os.environ:
        raise RuntimeError(
            "ISF_DISTRIBUTED_LOCK_BLOCK is defined, which turns off locking."
        )
    
    SERVER, CLIENT = get_locking_server_client()
    
    if SERVER["type"] == "file":
        return InterProcessLockNoWritePermission(name)
    elif SERVER["type"] == "redis":
        import redis
        return redis.lock.Lock(CLIENT, name, timeout=300)
    elif SERVER["type"] == "zookeeper":
        return CLIENT.Lock(name)
    else:
        raise RuntimeError(
            "supported server types are redis, zookeeper and file. "
            + "Current locking config is: {}".format(str(SERVER))
        )


def get_read_lock(name):
    """Fetch the correct read lock, depending on global locking server configuration.

    Args:
        name (str): The name of the lock.

    Returns:
        :py:class:`~data_base.distributed_lock.InterProcessLockNoWritePermission` | :py:class:`redis.lock` | :py:class:`kazoo.client.Lock`:
            The lock object.
    """
    if "ISF_DISTRIBUTED_LOCK_BLOCK" in os.environ:
        raise RuntimeError(
            "ISF_DISTRIBUTED_LOCK_BLOCK is defined, which turns off locking."
        )
    SERVER, CLIENT = get_locking_server_client()
    if SERVER["type"] == "file":
        return InterProcessLockNoWritePermission(name)
    elif SERVER["type"] == "redis":
        import redis
        return redis.lock.Lock(CLIENT, name, timeout=300)
    elif SERVER["type"] == "zookeeper":
        return CLIENT.ReadLock(name)
    else:
        raise RuntimeError(
            "supported server types are redis, zookeeper and file. "
            + "Current locking config is: {}".format(str(SERVER))
        )


def get_write_lock(name):
    """Fetch the correct write lock, depending on global locking server configuration.

    Args:
        name (str): The name of the lock.

    Returns:
        :py:class:`~data_base.distributed_lock.InterProcessLockNoWritePermission` | :py:class:`redis.lock` | :py:class:`kazoo.client.WriteLock`:
            The lock object.
    """
    if "ISF_DISTRIBUTED_LOCK_BLOCK" in os.environ:
        raise RuntimeError(
            "ISF_DISTRIBUTED_LOCK_BLOCK is defined, which turns off locking."
        )
    SERVER, CLIENT = get_locking_server_client()
    if SERVER["type"] == "file":
        return InterProcessLockNoWritePermission(name)

    elif SERVER["type"] == "redis":
        import redis
        return redis.lock.Lock(CLIENT, name, timeout=300)
    elif SERVER["type"] == "zookeeper":
        return CLIENT.WriteLock(name)
    else:
        raise RuntimeError(
            "supported server types are redis, zookeeper and file. "
            + "Current locking config is: {}".format(str(SERVER))
        )
