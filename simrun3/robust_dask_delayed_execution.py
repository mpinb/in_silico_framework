from model_data_base.distributed_lock import get_lock
import os
import warnings
import dask
import cloudpickle


def _set_value(managed_folder, k, value):
    k = '_'.join(k)
    with open(managed_folder.join(k), 'w') as f:
        f.write(cloudpickle.dumps(value))


def _get_value(managed_folder, k):
    k = '_'.join(k)
    with open(managed_folder.join(k), 'r') as f:
        return cloudpickle.loads(f.read())


def _get_keys(managed_folder):
    out = []
    for f in os.listdir(managed_folder):
        if not '_' in f:
            continue
        out.append(tuple(f.split('_')))
    return sorted(list(set(out)))


#def _increase_mdb_value(mdb, k, inc, __):
#    if not k in mdb.keys():
#        mdb[k] = 0
#    else:
#        mdb[k] = mdb[k] + inc

import warnings


def _assert_value(mdb, k, value, behaviour='warning'):
    v = _get_value(mdb, k)
    if not v == value:
        errstr = 'mdb[{}] is {} but expected {}'.format(str(k), str(v),
                                                        str(value))
        if behaviour == 'warning':
            warnings.warn(errstr)
        elif behaviour == 'error':
            raise RuntimeError(errstr)
        else:
            raise ValueError("behaviour must me 'warning' or 'error'")


@dask.delayed
def _wrapper(mdb, key_first_item):
    l = get_lock(os.path.join(mdb, key_first_item))
    l.acquire()
    _assert_value(mdb, (key_first_item, 'status'),
                  'not_started',
                  behaviour='warning')
    _set_value(mdb, (key_first_item, 'status'), 'started')
    l.release()
    d = _get_value(mdb, (key_first_item, 'obj'))
    d.compute(get=dask.get)
    l.acquire()
    _assert_value(mdb, (key_first_item, 'status'),
                  'started',
                  behaviour='warning')
    _set_value(mdb, (key_first_item, 'status'), 'finished')
    l.release()


class RobustDaskDelayedExecution:
    '''This class utilizes a managed folder to store delayed objects. It offers methods 
    to run them exactly once. The return value is not saved. Common usecase: Long runing, 
    data generating simulations are aborted (timeout on cluster, some error, ...) 
    and you want to complete the remaining tasks.'''

    def __init__(self, mdb):
        self.mdb = mdb

    def _check_state(self):
        pass

    def get_status(self):
        mdb = self.mdb
        keys = _get_keys(mdb)
        status = {k[0]: _get_value(mdb, k) for k in keys if k[1] == 'status'}
        return status

    def add_delayed_to_mdb(self, d):
        mdb = self.mdb
        keys = _get_keys(mdb)
        if len(keys) == 0:
            key = 0
        else:
            key = max({int(k[0]) for k in keys}) + 1
        key = str(key)
        _set_value(mdb, (key, 'status'), 'not_started')
        _set_value(mdb, (key, 'obj'), d)

    def reset_status(self, only_started=True):
        if only_started:
            status = self.get_status()
        keys = _get_keys(self.mdb)
        for k in keys:
            if k[1] == 'status':
                if only_started:
                    if not status[k[0]] == 'started':
                        continue
                _set_value(self.mdb, k, 'not_started')

    def run_mdb(self, error_started=True):
        ''
        mdb = self.mdb
        keys = _get_keys(mdb)
        status = {k[0]: _get_value(mdb, k) for k in keys if k[1] == 'status'}
        if 'started' in list(status.values()):
            if error_started:
                raise RuntimeError(
                    "Some of the simulations are already running!")
            else:
                warnings.warn("Some of the simulations are already running!")
        import six  #rieke
        ds = [
            _wrapper(mdb, k)
            for k, v in six.iteritems(status)
            if v == 'not_started'
        ]
        return ds