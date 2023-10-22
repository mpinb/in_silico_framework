from model_data_base.distributed_lock import get_lock
import os
import warnings
import dask


def _set_value(mdb, k, value):
    mdb[k] = value


def _increase_mdb_value(mdb, k, inc, __):
    if not k in list(mdb.keys()):
        mdb[k] = 0
    else:
        mdb[k] = mdb[k] + inc


def _assert_value(mdb, k, value, behaviour='warning'):
    v = mdb[k]
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
    l = get_lock(os.path.join(mdb.basedir, key_first_item))
    l.acquire()
    _assert_value(mdb, (key_first_item, 'status'),
                  'not_started',
                  behaviour='warning')
    _set_value(mdb, (key_first_item, 'status'), 'started')
    l.release()
    d = mdb[key_first_item, 'obj']
    d.compute(get=dask.get)
    l.acquire()
    _assert_value(mdb, (key_first_item, 'status'),
                  'started',
                  behaviour='warning')
    _set_value(mdb, (key_first_item, 'status'), 'finished')
    l.release()


class RobustDaskDelayedExecution:
    '''This class utilizes the model data base to store delayed objects. It offers methods 
    to run them exactly once. The return value is not saved. Common usecase: Long runing, 
    data generating simulations are aborted (timeout on cluster, some error, ...) 
    and you want to complete the remaining tasks.'''

    def __init__(self, mdb):
        self.mdb = mdb

    def _check_state(self):
        pass

    def get_status(self):
        m = self.mdb
        status = {k[0]: m[k] for k in list(m.keys()) if k[1] == 'status'}
        return status

    def add_delayed_to_mdb(self, d):
        mdb = self.mdb
        if len(list(mdb.keys())) == 0:
            key = 0
        else:
            key = max({int(k[0]) for k in list(mdb.keys())}) + 1
        key = str(key)
        mdb[key, 'status'] = 'not_started'
        mdb[key, 'obj'] = d

    def run_mdb(self, error_started=True):
        ''
        import six
        mdb = self.mdb
        status = {k[0]: mdb[k] for k in list(mdb.keys()) if k[1] == 'status'}
        if 'started' in list(status.values()):
            if error_started:
                raise RuntimeError(
                    "Some of the simulations are already running!")
            else:
                warnings.warn("Some of the simulations are already running!")
        ds = [
            _wrapper(mdb, k)
            for k, v in six.iteritems(status)
            if v == 'not_started'
        ]
        return ds