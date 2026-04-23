from data_base import DataBase, get_db_by_unique_id
import tempfile, os, shutil
import pytest


def assert_search_db_did_not_fail(data_base_register):
    keys = list(data_base_register.keys())
    keys = [k for k in keys if isinstance(k, tuple)]
    #for k in keys: print (dbr.db[k])
    assert not keys


def test_added_db_can_be_found_by_id(data_base_register, tmp_path):
    p1 = os.path.join(tmp_path, 'test1')
    p2 = os.path.join(tmp_path, 'test1', 'test2')
    p3 = os.path.join(tmp_path, 'test2', 'test2')
    db1 = DataBase(p1)
    db2 = DataBase(p2)
    db3 = DataBase(p3)

    for db in [db1, db2, db3]:
        db._register_this_database()

    assert get_db_by_unique_id(db1.get_id()).basedir == p1
    assert get_db_by_unique_id(db2.get_id()).basedir == p2
    assert get_db_by_unique_id(db3.get_id()).basedir == p3

    db4 = DataBase(os.path.join(tmp_path, 'test4'))
    db4._register_this_database()
    assert get_db_by_unique_id(db4.get_id()).basedir == db4.basedir
    assert_search_db_did_not_fail(data_base_register)

def test_unknown_id_raises_KeyError(data_base_register):

    with pytest.raises(KeyError):
        get_db_by_unique_id('bla')
    assert_search_db_did_not_fail(data_base_register)


# test_search_dbs_finds_dbs