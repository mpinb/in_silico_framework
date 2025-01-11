from data_base.distributed_lock import get_lock
import os
import warnings
import dask
import cloudpickle


def _set_value(managed_folder, k, value):
    """:skip-doc:"""
    k = '_'.join(k)
    with open(managed_folder.join(k), 'w') as f:
        f.write(cloudpickle.dumps(value))


def _get_value(managed_folder, k):
    """:skip-doc:"""
    k = '_'.join(k)
    with open(managed_folder.join(k), 'r') as f:
        return cloudpickle.loads(f.read())


def _get_keys(managed_folder):
    """:skip-doc:"""
    out = []
    for f in os.listdir(managed_folder):
        if not '_' in f:
            continue
        out.append(tuple(f.split('_')))
    return sorted(list(set(out)))


#def _increase_db_value(db, k, inc, __):
#    if not k in db.keys():
#        db[k] = 0
#    else:
#        db[k] = db[k] + inc

def _assert_value(db, k, value, behaviour='warning'):
    v = _get_value(db, k)
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
    l = get_lock(os.path.join(db, key_first_item))
    l.acquire()
    _assert_value(db, (key_first_item, 'status'),
                  'not_started',
                  behaviour='warning')
    _set_value(db, (key_first_item, 'status'), 'started')
    l.release()
    d = _get_value(db, (key_first_item, 'obj'))
    d.compute(scheduler="synchronous")
    l.acquire()
    _assert_value(db, (key_first_item, 'status'),
                  'started',
                  behaviour='warning')
    _set_value(db, (key_first_item, 'status'), 'finished')
    l.release()


class RobustDaskDelayedExecution:
    '''Execute dask delayed objects in a robust way.
    
    This class utilizes :py:class:`data_base.IO.LoaderDumper.just_create_folder.ManagedFolder` objects to store delayed objects. 
    It offers methods to run them exactly once. The return value is not saved if the dask delayeds objects don't save them. 
    
    This is used for long runing data generating simulations that can get interrupted (e.g. timeout on an HPC cluster, some error ...) 
    and you want to complete the remaining tasks later.
    
    Attributes:
        db (:py:class:`data_base.dataBase`): 
            The database containing the :py:class:`~data_base.IO.LoaderDumper.just_create_folder.ManagedFolder` objects, 
            which in turn contain the dask delayed objects.
    '''

    def __init__(self, db):
        """
        Args:
            db (:py:class:`data_base.dataBase`): 
                The database containing the :py:class:`~data_base.IO.LoaderDumper.just_create_folder.ManagedFolder` objects,
                which in turn contain the dask delayed objects.
        """
        self.db = db

    def _check_state(self):
        """:skip-doc:"""
        pass

    def get_status(self):
        """Get the status on the computation of the delayed objects.
        
        Returns:
            dict: A dictionary with the keys being the keys of the delayed objects and the values being the status of the computation. 
            Possible values are ``'not_started'``, ``'started'``, ``'finished'``.
        """
        db = self.db
        keys = _get_keys(db)
        status = {k[0]: _get_value(db, k) for k in keys if k[1] == 'status'}
        return status

    def add_delayed_to_db(self, d):
        """Add a delayed object to the database.
        
        Args:
            d (dask.delayed): The delayed object to be added.
        """
        db = self.db
        keys = _get_keys(db)
        if len(keys) == 0:
            key = 0
        else:
            key = max({int(k[0]) for k in keys}) + 1
        key = str(key)
        _set_value(db, (key, 'status'), 'not_started')
        _set_value(db, (key, 'obj'), d)

    def reset_status(self, only_started=True):
        """Reset the status of the delayed objects to ``'not_started'``.
        
        Args:
            only_started (bool): If ``True`` only the status of the delayed objects that are currently running is reset.
        """
        if only_started:
            status = self.get_status()
        keys = _get_keys(self.db)
        for k in keys:
            if k[1] == 'status':
                if only_started:
                    if not status[k[0]] == 'started':
                        continue
                _set_value(self.db, k, 'not_started')

    def run_db(self, error_started=True):
        """Run all delayed objects in the database.
        
        Args:
            error_started (bool): If ``True`` (default), an error is raised if some of the delayed objects are already running.
            
        Returns:
            list: A list of the delayed objects that are executed
        """
        db = self.db
        keys = _get_keys(db)
        status = {k[0]: _get_value(db, k) for k in keys if k[1] == 'status'}
        if 'started' in list(status.values()):
            if error_started:
                raise RuntimeError(
                    "Some of the simulations are already running!")
            else:
                warnings.warn("Some of the simulations are already running!")
        import six  #rieke
        ds = [
            _wrapper(db, k)
            for k, v in six.iteritems(status)
            if v == 'not_started'
        ]
        return ds