from data_base.model_data_base.model_data_base import ModelDataBase, MdbException
from data_base.data_base import get_db_by_unique_id
import tempfile, os, shutil
from data_base.data_base_register import _get_db_register, DataBaseRegister, register_db
import pytest


def assert_search_db_did_not_fail(dbr):
    keys = list(dbr.keys())
    keys = [k for k in keys if isinstance(k, tuple)]
    #for k in keys: print (dbr.db[k])
    assert not keys


class TestModelDataBaseRegister:

    def setup_class(self):
        self.basetempdir = tempfile.mkdtemp()

    def teardown_class(self):
        shutil.rmtree(self.basetempdir)

# commented out, since we now define dbr in the module itself
#     def test_get_db_register_raises_db_exception_if_there_is_no_register(self):
#         self.assertRaises(ModelDataBaseException, lambda:  _get_db_register(self.basetempdir))

    def test_added_db_can_be_found_by_id(self):
        p1 = os.path.join(self.basetempdir, 'test1')
        p2 = os.path.join(self.basetempdir, 'test1', 'test2')
        p3 = os.path.join(self.basetempdir, 'test2', 'test2')
        db1 = ModelDataBase(p1)
        db2 = ModelDataBase(p2)
        db3 = ModelDataBase(p3)

        for db in [db1, db2, db3]:
            db._register_this_database()

        dbr = DataBaseRegister(self.basetempdir)
        assert get_db_by_unique_id(db1.get_id()).basedir == p1
        assert get_db_by_unique_id(db2.get_id()).basedir == p2
        assert get_db_by_unique_id(db3.get_id()).basedir == p3

        db4 = ModelDataBase(os.path.join(self.basetempdir, 'test4'))
        db4._register_this_database()
        assert get_db_by_unique_id(db4.get_id()).basedir == db4.basedir
        assert_search_db_did_not_fail(dbr)

    def test_unknown_id_raises_KeyError(self):
        dbr = DataBaseRegister(self.basetempdir)

        with pytest.raises(KeyError):
            get_db_by_unique_id('bla')
        assert_search_db_did_not_fail(dbr)


# test_search_dbs_finds_dbs