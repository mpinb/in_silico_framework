from __future__ import absolute_import
from .tuplecloudsqlitedict import SqliteDict
import os

###################################################
# additional locking
###################################################

# maybe this locking is over the top and sqlite already handels this well,
# however I sometimes got OperationalError: database is locked exceptions.
# it is now optional to switch on an aditional filebased lock.
# This has the disadvantage that it also blocks concurrent reading.

locking = True
if locking:
    from .. import distributed_lock

# def aquire_lock(path):
#     if not locking: return
#     path = path + '.lock'
#     mylock = distributed_lock.get_lock(path)
#     mylock.acquire()
#     return mylock


def aquire_read_lock(path):
    if not locking:
        return
    path = path + '.lock'
    mylock = distributed_lock.get_read_lock(path)
    mylock.acquire()
    return mylock


def aquire_write_lock(path):
    if not locking:
        return
    path = path + '.lock'
    mylock = distributed_lock.get_write_lock(path)
    mylock.acquire()
    return mylock


def release_lock(mylock):
    if not locking:
        return
    mylock.release()
    #try:
    #    mylock.release()
    #except ThreadError as e:
    #    warnings.warn(str(e))


class SQLiteBackend(object):

    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            sqlitedict = self._get_sql()  # make sure, sqlite-file exists
            self._close_sql(sqlitedict)

    def _get_sql(self, readonly=True):
        if readonly:
            self.lock = aquire_read_lock(self.path)
        else:
            self.lock = aquire_write_lock(self.path)
        if readonly:
            flag = 'r'
        else:
            flag = 'c'
        return SqliteDict(self.path, autocommit=True, flag=flag)

    def _close_sql(self, sqlitedict):
        sqlitedict.close()
        release_lock(self.lock)

    def __getitem__(self, arg):
        '''Backend method to retrive item from the database'''
        dict_ = self._vectorized_getitem([arg])
        assert len(dict_) == 1
        return list(dict_.values())[0]

    def _vectorized_getitem(self, keys):
        '''this allows to get many values at once, reducing the overhead of repeated 
        opening and closing the connection'''
        # with DelayedKeyboardInterrupt():
        try:
            sqllitedict = self._get_sql()
            dummy = {key: sqllitedict[key] for key in keys}
        except:
            raise
        finally:
            try:
                self._close_sql(sqllitedict)
            except:
                pass
        return dummy

    def __setitem__(self, key, item):
        '''Backend method to add a key-value pair to the sqlite database'''
        self._vectorized_setitem({key: item})

    def _vectorized_setitem(self, dict_):
        '''this allows to set many values at once, reducing the overhead of repeated 
        opening and closing the connection'''
        #with DelayedKeyboardInterrupt():
        import six
        try:
            sqllitedict = self._get_sql(readonly=False)
            for k, v in six.iteritems(dict_):
                sqllitedict[k] = v
        except:
            raise
        finally:
            try:
                self._close_sql(sqllitedict)
            except:
                pass

    def __delitem__(self, arg):
        '''Backend method to delete item from the sqlite database.'''
        self._vectorized_delitem([arg])

    def _vectorized_delitem(self, keys):
        '''this allows to delete many values at once, reducing the overhead of repeated 
        opening and closing the connection'''
        # with DelayedKeyboardInterrupt():
        try:
            sqllitedict = self._get_sql(readonly=False)
            for k in keys:
                del sqllitedict[k]
        except:
            raise
        finally:
            try:
                self._close_sql(sqllitedict)
            except:
                pass

    def keys(self):
        # with DelayedKeyboardInterrupt():
        try:
            sqllitedict = self._get_sql()
            keys = list(sqllitedict.keys())
            #                return sorted(keys) # causes an error if some keys are tuples and others are strings
            return keys
        finally:
            try:
                self._close_sql(sqllitedict)
            except:
                pass


class InMemoryBackend(object):

    def __init__(self, backend, keys='all'):
        if keys == 'all':
            keys = list(backend.keys())
        self._db = backend._vectorized_getitem(keys)

    def __getitem__(self, arg):
        '''Backend method to retrive item from the database'''
        return self._db[arg]

    def _vectorized_getitem(self, keys):
        '''this allows to get many values at once, reducing the overhead of repeated 
        opening and closing the connection'''
        return {k: self._db[k] for k in keys}

    def __setitem__(self, key, item):
        '''Backend method to add a key-value pair to the sqlite database'''
        errstr = 'This is the in-memory view on a database. You cannot change items.'
        raise NotImplementedError(errstr)

    def _vectorized_setitem(self, dict_):
        '''this allows to set many values at once, reducing the overhead of repeated 
        opening and closing the connection'''
        errstr = 'This is the in-memory view on a database. You cannot change items.'
        raise NotImplementedError(errstr)

    def __delitem__(self, arg):
        '''Backend method to delete item from the sqlite database.'''
        errstr = 'This is the in-memory view on a database. You cannot change items.'
        raise NotImplementedError(errstr)

    def _vectorized_delitem(self, keys):
        '''this allows to delete many values at once, reducing the overhead of repeated 
        opening and closing the connection'''
        errstr = 'This is the in-memory view on a database. You cannot change items.'
        raise NotImplementedError(errstr)

    def keys(self):
        return list(self._db.keys())
