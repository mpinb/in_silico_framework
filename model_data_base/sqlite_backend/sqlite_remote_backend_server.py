import os
import argparse
import zmq
from collections import defaultdict
from model_data_base import distributed_lock
import sqlite3
import cloudpickle
import yaml
import sys
from compatibility import YamlLoader

try:
    config_path = os.environ['ISF_MDB_CONFIG']
except KeyError:
    # module is likely called upon from import instead of being run directly -> this key is not necessarily set then
    sys.exit(1)
with open(os.environ['ISF_MDB_CONFIG'], 'r') as f:
    config = yaml.load(f, Loader=YamlLoader)
# we here assume backend is sqlite_remote, as otherwise this module would not be loaded
assert config['backend']['type'] == 'sqlite_remote'
ip, port = config['backend']['url'].split(':')


class SQLiteDict:
    '''This is a minimal version of SQLiteDict. It does not serialize or unserialize data.
    It does not close the connection automatically.'''
    PRAGMA = 'PRAGMA journal_mode = %s' % 'DELETE'
    MAKE_TABLE = 'CREATE TABLE IF NOT EXISTS "%s" (key TEXT PRIMARY KEY, value BLOB)' % 'unnamed'
    GET_ITEM = 'SELECT value FROM "%s" WHERE key = ?' % 'unnamed'
    ADD_ITEM = 'REPLACE INTO "%s" (key, value) VALUES (?,?)' % 'unnamed'
    DEL_ITEM = 'DELETE FROM "%s" WHERE key = ?' % 'unnamed'
    GET_KEYS = 'SELECT key FROM "%s" ORDER BY rowid' % 'unnamed'

    def __init__(self, path):
        self.path = path
        conn = sqlite3.connect(self.path,
                               isolation_level=None,
                               check_same_thread=False)
        conn.text_factory = str
        conn.execute(SQLiteDict.PRAGMA)
        conn.execute(SQLiteDict.MAKE_TABLE)
        cursor = conn.cursor()
        self.conn = conn
        self.cursor = cursor

    def __getitem__(self, key):
        return self.cursor.execute(SQLiteDict.GET_ITEM, (key,)).fetchone()[0]

    def __setitem__(self, key, value):
        self.conn.execute(SQLiteDict.ADD_ITEM, (key, value))
        # self.conn.commit()

    def __delitem__(self, key):
        self.conn.execute(SQLiteDict.DEL_ITEM, (key,))
        # self.conn.commit()

    def keys(self):
        return [
            k[0] for k in self.cursor.execute(SQLiteDict.GET_KEYS).fetchall()
        ]

    def close(self):
        self.conn.close()


context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind('tcp://*:{}'.format(port))

mdbs = {}
cache = defaultdict(dict)
locks = {}


def add_mdb(path):
    lock = aquire_lock(path)
    locks[path] = lock
    mdbs[path] = SQLiteDict(path)


def aquire_lock(path):
    path = path + '.lock'
    mylock = distributed_lock.get_lock(path)
    # mylock.acquire()
    return mylock


def release_lock(mylock):
    mylock.release()


while True:
    msg = socket.recv()
    print(msg)
    try:
        setget, path, rest = msg.split('\x00\x00', 2)
    except:
        socket.send('ERROR')
        continue
    if not path in mdbs:
        add_mdb(path)
    if setget == 'SET':
        try:
            key, value = rest.split('\x00', 1)
        except:
            socket.send('ERROR')
            continue
        mdbs[path][key] = value
        socket.send('DONE')
        mdbs[path].conn.commit()
        cache[path][key] = value
    elif setget == 'DEL':
        key = rest
        try:
            del cache[path][key]
        except KeyError:
            pass
        try:
            del mdbs[path][key]
        except KeyError:
            socket.send('ERROR')
            continue
        socket.send('DONE')
        mdbs[path].conn.commit()
    elif setget == 'GET':
        key = rest
        try:
            value = cache[path][key]
        except KeyError:
            pass
        try:
            value = mdbs[path][key]
        except:
            socket.send('ERROR')
            continue
        cache[path][key] = value
        socket.send(value)
    elif setget == 'KEYS':
        key = rest
        print('sending message')
        socket.send(cloudpickle.dumps(list(mdbs[path].keys())))
    else:
        raise ValueError()