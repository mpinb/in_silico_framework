import distributed
# import fasteners
# import redis
import yaml
import os
import warnings

if 'ISF_DISTRIBUTED_LOCK_CONFIG' in os.environ:
    config_path = os.environ['ISF_DISTRIBUTED_LOCK_CONFIG']
    with open(os.environ['ISF_DISTRIBUTED_LOCK_CONFIG'], 'r') as f:
        config = yaml.load(f)
else:
    warnings.warn('environment variable ISF_DISTRIBUTED_LOCK_CONFIG is not set. ' + 
                  'Falling back to default configuration.')
    config = [dict(type = 'redis', config = dict(host = 'spock', port = 8885, socket_timeout = 1)),
              dict(type = 'redis', config = dict(host = 'localhost', port = 6379, socket_timeout = 1)),
              dict(type = 'file')]


def get_client():
    for server in config:
        print('trying to connect to distributed locking server {}'.format(str(server)))
        if server['type'] == 'redis':
            import redis
            try:
                c = redis.StrictRedis(**server['config'])
                c.client_list()
                print ('success!')
                return server, c
            except (redis.exceptions.TimeoutError, redis.exceptions.ConnectionError):
                pass
        elif server['type'] == 'file':
            warnings.warn('Using file based locking.'
            'Please be careful on nfs mounts as file based locking has issues in this case.')
            return server, None
        elif server['type'] == 'zookeeper':
            import kazoo.client
            zk = kazoo.client.KazooClient(**server['config'])
            zk.start()
            print ('success!')
            return server, zk
        else:
            raise NotImplementedError()
    raise RuntimeError('could not connect to a locking server.')

server, client = get_client()

def update_config(c):
    global server
    global client
    global config
    config = c
    server, client = get_client()

def get_lock(name):
    if server['type'] == 'file':
        import fasteners
        return fasteners.InterProcessLock(name)
    elif server['type'] == 'redis':
        import redis
        return redis.lock.Lock(client, name, timeout = 300)
    elif server['type'] == 'zookeeper':
        return client.Lock(name)
    else:
        raise RuntimeError('supported server types are redis, zookeeper and file. ' + 
            'Current locking config is: {}'.format(str(server)))
        
def get_read_lock(name):
    if server['type'] == 'file':
        import fasteners
        return fasteners.InterProcessLock(name)
    elif server['type'] == 'redis':
        import redis
        return redis.lock.Lock(client, name, timeout = 300)
    elif server['type'] == 'zookeeper':
        return client.ReadLock(name)
    else:
        raise RuntimeError('supported server types are redis, zookeeper and file. ' + 
            'Current locking config is: {}'.format(str(server)))
        
def get_write_lock(name):
    if server['type'] == 'file':
        import fasteners
        return fasteners.InterProcessLock(name)
    elif server['type'] == 'redis':
        import redis
        return redis.lock.Lock(client, name, timeout = 300)
    elif server['type'] == 'zookeeper':
        return client.WriteLock(name)
    else:
        raise RuntimeError('supported server types are redis, zookeeper and file. ' + 
            'Current locking config is: {}'.format(str(server)))
