import distributed

# import fasteners
# import redis
import yaml
import os
import warnings
from compatibility import YamlLoader
import logging
logger = logging.getLogger("ISF").getChild(__name__)

if 'ISF_DISTRIBUTED_LOCK_BLOCK' in os.environ:
    pass
elif 'ISF_DISTRIBUTED_LOCK_CONFIG' in os.environ:
    config_path = os.environ['ISF_DISTRIBUTED_LOCK_CONFIG']
    with open(os.environ['ISF_DISTRIBUTED_LOCK_CONFIG'], 'r') as f:
        config = yaml.load(f, Loader=YamlLoader)
else:
    logger.warning(
        "Environment variable ISF_DISTRIBUTED_LOCK_CONFIG is not set. " +
        "Falling back to default configuration.")
    config = [
        dict(type="redis",
             config=dict(host="spock", port=8885, socket_timeout=1)),
        dict(type="redis",
             config=dict(host="localhost", port=6379, socket_timeout=1)),
        dict(type="file"),
    ]


def get_client():
    if 'ISF_DISTRIBUTED_LOCK_BLOCK' in os.environ:
        return None, None
    for server in config:
        logger.info("trying to connect to distributed locking server {}".format(
            str(server)))
        if server["type"] == "redis":
            import redis

            try:
                c = redis.StrictRedis(**server["config"])
                c.client_list()
                print("success!")
                return server, c
            except (redis.exceptions.TimeoutError,
                    redis.exceptions.ConnectionError):
                pass
        elif server["type"] == "file":
            logger.warning(
                "Using file based locking. "
                "Please be careful on nfs mounts as file based locking has issues in this case."
            )
            return server, None
        elif server["type"] == "zookeeper":
            import kazoo.client

            zk = kazoo.client.KazooClient(**server["config"])
            zk.start()
            logger.info("success!")
            return server, zk
        else:
            raise NotImplementedError()
    raise RuntimeError("could not connect to a locking server.")


server, client = get_client()


def update_config(c):
    """
    Update the global configuration variables with the provided configuration.

    Args:
        c (dict): A dictionary containing the new configuration values.

    Returns:
        None
    """
    global server
    global client
    global config
    config = c
    server, client = get_client()


def get_lock(name):
    if 'ISF_DISTRIBUTED_LOCK_BLOCK' in os.environ:
        raise RuntimeError('ISF_DISTRIBUTED_LOCK_BLOCK is defined, which turns off locking.')
    if server['type'] == 'file':
        import fasteners

        return fasteners.InterProcessLock(name)
    elif server["type"] == "redis":
        import redis

        return redis.lock.Lock(client, name, timeout=300)
    elif server["type"] == "zookeeper":
        return client.Lock(name)
    else:
        raise RuntimeError(
            "supported server types are redis, zookeeper and file. " +
            "Current locking config is: {}".format(str(server)))


def get_read_lock(name):
    if 'ISF_DISTRIBUTED_LOCK_BLOCK' in os.environ:
        raise RuntimeError('ISF_DISTRIBUTED_LOCK_BLOCK is defined, which turns off locking.')    
    if server['type'] == 'file':
        import fasteners

        return fasteners.InterProcessLock(name)
    elif server["type"] == "redis":
        import redis

        return redis.lock.Lock(client, name, timeout=300)
    elif server["type"] == "zookeeper":
        return client.ReadLock(name)
    else:
        raise RuntimeError(
            "supported server types are redis, zookeeper and file. " +
            "Current locking config is: {}".format(str(server)))


def get_write_lock(name):
    if 'ISF_DISTRIBUTED_LOCK_BLOCK' in os.environ:
        raise RuntimeError('ISF_DISTRIBUTED_LOCK_BLOCK is defined, which turns off locking.')    
    if server['type'] == 'file':
        import fasteners

        return fasteners.InterProcessLock(name)
    elif server["type"] == "redis":
        import redis

        return redis.lock.Lock(client, name, timeout=300)
    elif server["type"] == "zookeeper":
        return client.WriteLock(name)
    else:
        raise RuntimeError(
            "supported server types are redis, zookeeper and file. " +
            "Current locking config is: {}".format(str(server)))
