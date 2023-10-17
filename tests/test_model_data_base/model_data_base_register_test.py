from .context import *
from model_data_base.model_data_base import ModelDataBase, MdbException
from model_data_base.model_data_base_register import _get_mdb_register, \
        ModelDataBaseRegister, get_mdb_by_unique_id, register_mdb
import pytest

def assert_search_mdb_did_not_fail(mdbr):
    keys = list(mdbr.mdb.keys())
    keys = [k for k in keys if isinstance(k, tuple)]
    #for k in keys: print (mdbr.mdb[k])
    assert(not keys)
    
class TestModelDataBaseRegister:       
    def setup_class(self):        
        self.basetempdir = tempfile.mkdtemp()
        
    def teardown_class(self):
        shutil.rmtree(self.basetempdir)     
        
# commented out, since we now define mdbr in the module itself
#     def test_get_mdb_register_raises_mdb_exception_if_there_is_no_register(self):
#         self.assertRaises(MdbException, lambda:  _get_mdb_register(self.basetempdir))
    
    def test_added_mdb_can_be_found_by_id(self):
        p1 = os.path.join(self.basetempdir, 'test1')
        p2 = os.path.join(self.basetempdir, 'test1', 'test2')
        p3 = os.path.join(self.basetempdir, 'test2', 'test2')
        mdb1 = ModelDataBase(p1)
        mdb2 = ModelDataBase(p2)
        mdb3 = ModelDataBase(p3)
        
        for mdb in [mdb1, mdb2, mdb3]: mdb._register_this_database()
        
        mdbr = ModelDataBaseRegister(self.basetempdir)
        
        assert get_mdb_by_unique_id(mdb1.get_id()).basedir == p1
        assert get_mdb_by_unique_id(mdb2.get_id()).basedir == p2
        assert get_mdb_by_unique_id(mdb3.get_id()).basedir == p3
        
        mdb4 = ModelDataBase(os.path.join(self.basetempdir, 'test4'))
        register_mdb(mdb4)
        assert get_mdb_by_unique_id(mdb4.get_id()).basedir == mdb4.basedir
        assert_search_mdb_did_not_fail(mdbr)
        
    def test_unknown_id_raises_KeyError(self):
        mdbr = ModelDataBaseRegister(self.basetempdir)
                
        with pytest.raises(KeyError):
            get_mdb_by_unique_id('bla')
        assert_search_mdb_did_not_fail(mdbr)
        
        
# test_search_mdbs_finds_mdbs