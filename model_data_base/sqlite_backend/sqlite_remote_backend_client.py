import os
import zmq
import cloudpickle
import yaml
import sys
from compatibility import YamlLoader
#context = zmq.Context()
#socket = context.socket(zmq.REQ)
#socket.connect('tcp://130.183.178.36:5555')

try:
    config_path = os.environ['ISF_MDB_CONFIG']
except KeyError:
    # the key ISF_MDB_CONFIG is not set
    # likely, the module is called upon from an import
    sys.exit(1)
with open(os.environ['ISF_MDB_CONFIG'], 'r') as f:
    config = yaml.load(f, Loader=YamlLoader)

assert config['backend']['type'] == 'sqlite_remote'
url = config['backend']['url']


def check_key(key):
    if isinstance(key, tuple):
        for k in key:
            if not isinstance(k, str):
                raise ValueError(
                    "keys have to be strings or a tuple of strings")
            if '@' in k:
                raise ValueError(
                    "keys are not allowed to contain the letter '@'")
    elif isinstance(key, str):
        check_key(tuple([key]))
    else:
        raise ValueError("keys have to be strings or a tuple of strings")


def convert_key(key):
    check_key(key)
    if isinstance(key, tuple):
        key = '@'.join(key)
    return key


class SQLiteBackendRemote(object):

    def __init__(self, path, url='tcp://{}'.format(url)):
        self.path = path
        self.url = url
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.url)

    def __getitem__(self, key):
        '''Backend method to retrive item from the database'''
        key = convert_key(key)
        message = 'GET' + '\x00\x00' + self.path + '\x00\x00' + key
        self.socket.send(message)
        message = self.socket.recv()
        if message == 'ERROR':
            raise KeyError(key)
        return cloudpickle.loads(message)

    def __setitem__(self, key, item):
        '''Backend method to add a key-value pair to the sqlite database'''
        key = convert_key(key)
        message = 'SET' + '\x00\x00' + self.path + '\x00\x00' + key + '\x00' + cloudpickle.dumps(
            item)
        self.socket.send(message)
        if not self.socket.recv() == 'DONE':
            raise RuntimeError()

    def __delitem__(self, key):
        '''Backend method to delete item from the sqlite database.'''
        key = convert_key(key)
        message = 'DEL' + '\x00\x00' + self.path + '\x00\x00' + key
        self.socket.send(message)
        if not self.socket.recv() == 'DONE':
            raise RuntimeError()

    def keys(self):
        message = 'KEYS' + '\x00\x00' + self.path + '\x00\x00'
        self.socket.send(message)
        keys = cloudpickle.loads(self.socket.recv())
        out = []
        for l in keys:
            if '@' in l:
                out.append(tuple(l.split('@')))
            else:
                out.append(l)
        return out