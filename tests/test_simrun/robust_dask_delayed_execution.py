from data_base.distributed_lock import get_lock
import os
import warnings
import dask


def _set_value(db, k, value):
    db[k] = value


def _increase_db_value(db, k, inc, __):
    if not k in list(db.keys()):
        db[k] = 0
    else:
        db[k] = db[k] + inc


def _assert_value(db, k, value, behaviour='warning'):
    v = db[k]
    if not v == value:
        errstr = 'db[{}] is {} but expected {}'.format(str(k), str(v),
                                                        str(value))
        if behaviour == 'warning':
            warnings.warn(errstr)
        elif behaviour == 'error':
            raise RuntimeError(errstr)
        else:
            raise ValueError("behaviour must me 'warning' or 'error'")


@dask.delayed
def _wrapper(db, key_first_item):
    l = get_lock(os.path.join(db.basedir, key_first_item))
    l.acquire()
    _assert_value(db, (key_first_item, 'status'),
                  'not_started',
                  behaviour='warning')
    _set_value(db, (key_first_item, 'status'), 'started')
    l.release()
    d = db[key_first_item, 'obj']
    d.compute(scheduler="synchronous")
    l.acquire()
    _assert_value(db, (key_first_item, 'status'),
                  'started',
                  behaviour='warning')
    _set_value(db, (key_first_item, 'status'), 'finished')
    l.release()


class RobustDaskDelayedExecution:
    '''This class utilizes the model data base to store delayed objects. It offers methods 
    to run them exactly once. The return value is not saved. Common usecase: Long runing, 
    data generating simulations are aborted (timeout on cluster, some error, ...) 
    and you want to complete the remaining tasks.'''

    def __init__(self, db):
        self.db = db

    def _check_state(self):
        pass

    def get_status(self):
        m = self.db
        status = {k[0]: m[k] for k in list(m.keys()) if k[1] == 'status'}
        return status

    def add_delayed_to_db(self, d):
        db = self.db
        if len(list(db.keys())) == 0:
            key = 0
        else:
            key = max({int(k[0]) for k in list(db.keys())}) + 1
        key = str(key)
        db[key, 'status'] = 'not_started'
        db[key, 'obj'] = d

    def run_db(self, error_started=True):
        ''
        import six
        db = self.db
        status = {k[0]: db[k] for k in list(db.keys()) if k[1] == 'status'}
        if 'started' in list(status.values()):
            if error_started:
                raise RuntimeError(
                    "Some of the simulations are already running!")
            else:
                warnings.warn("Some of the simulations are already running!")
        ds = [
            _wrapper(db, k)
            for k, v in six.iteritems(status)
            if v == 'not_started'
        ]
        return ds