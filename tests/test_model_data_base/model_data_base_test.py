from .context import *
from model_data_base.model_data_base import ModelDataBase, MdbException
from  model_data_base import model_data_base_register 
import model_data_base.IO.LoaderDumper.to_pickle  as to_pickle
from . import decorators
import unittest
import os, shutil
import numpy as np
import tempfile
import warnings
from pandas.util.testing import assert_frame_equal
from model_data_base import IO
import subprocess

class TestModelDataBase(unittest.TestCase):       
    def setUp(self):        
        self.path_fresh_mdb = tempfile.mkdtemp()
        self.fresh_mdb = ModelDataBase(self.path_fresh_mdb)
        
    def tearDown(self):
        shutil.rmtree(self.path_fresh_mdb)
        
#     def test_register_modes(self):
#         self.assertRaises(MdbException, \
#                           lambda: ModelDataBase(self.path_fresh_mdb, register = "on_every_init"))
#         self.assertRaises(MdbException, \
#                           lambda: ModelDataBase(os.path.join(self.path_fresh_mdb, 'subfolder'),\
#                                                   register = "on_every_init"), register = "on_first_init")
#         ModelDataBase(self.path_fresh_mdb, register = "on_first_init")
#         with warnings.catch_warnings() as w:
#             ModelDataBase(self.path_fresh_mdb, register = "try_on_every_init")
#             ModelDataBase(os.path.join(self.path_fresh_mdb, 'subfolder'),\
#                                                   register = "try_on_every_init")
#             assert(len(w >= 2))
#             
#     def test_register_works(self):
#         mdbr = model_data_base_register.ModelDataBaseRegister(self.path_fresh_mdb)
#         self.assertIn(self.fresh_msdb._unique_id, mdbr.mdb.keys())
#         submdb = self.fresh_mdb.create_sub_mdb("something")
#         self.assertIn(submdb._unique_id, mdbr.mdb.keys())
         
    def test_unique_id_is_set_on_initialization(self):
        self.assertTrue(self.fresh_mdb._unique_id is not None)
         
    def test_unique_id_stays_the_same_on_reload(self):
        mdb1 = self.fresh_mdb
        mdb2 = ModelDataBase(self.path_fresh_mdb)
        self.assertEqual(mdb1._unique_id, mdb2._unique_id)
         
    def test_new_unique_id_is_generated_if_it_is_not_set_yet(self):
        self.fresh_mdb._unique_id = None
        self.fresh_mdb.save_db()
        self.assertTrue(self.fresh_mdb._unique_id is None)
        mdb = ModelDataBase(self.path_fresh_mdb)
        self.assertTrue(mdb._unique_id is not None)
         
    def test_get_dumper_string_by_dumper_module(self):
        '''dumper string should be the modules name wrt IO.LoaderDumpers'''
        s1 = IO.LoaderDumper.get_dumper_string_by_dumper_module(to_pickle)
        s2 = 'to_pickle'
        self.assertEqual(s1, s2)
     
    def test_get_dumper_string_by_savedir(self):
        '''dumper string should be the same if it is determined
        post hoc (by providing the path to an already existing folder)
        or from the module reference directly.'''
        self.fresh_mdb.setitem('test', 1, dumper = to_pickle)
        s1 = self.fresh_mdb._detect_dumper_string_of_existing_key('test')
        s2 = IO.LoaderDumper.get_dumper_string_by_dumper_module(to_pickle)
        self.assertEqual(s1, s2)
         
    def test_can_detect_self_as_dumper(self):
        '''dumper string should be the same if it is determined
        post hoc (by providing the path to an already existing folder)
        or from the module reference directly.'''
        self.fresh_mdb.setitem('test', 1, dumper = 'self')
        s1 = self.fresh_mdb._detect_dumper_string_of_existing_key('test')
        self.assertEqual(s1, 'self')
         
    def test_metadata_update(self):
        '''the method _update_metadata_if_necessary has the purpose of
        providing a smooth transition from databases, that had not implemented
        metadata to the newer version. This function should not overwrite
        existing metadata'''
        self.fresh_mdb.setitem('test', 1, dumper = 'self')
        self.fresh_mdb.setitem('test2', 1, dumper = to_pickle)
        msg1= "{} =/= {}".format(self.fresh_mdb.metadata['test']['version'], model_data_base.get_versions()['version'])
        msg2= "{} =/= {}".format(self.fresh_mdb.metadata['test2']['version'], model_data_base.get_versions()['version'])
        msg_git = "\nDid the commit turn dirty during testing?\n"
        msg_git += subprocess.check_output(['git status'], shell=True).decode('utf-8')
        self.assertEqual(self.fresh_mdb.metadata['test']['version'], \
                         model_data_base.get_versions()['version'],
                         msg=msg1+msg_git)
        self.assertEqual(self.fresh_mdb.metadata['test2']['version'], \
                         model_data_base.get_versions()['version'],
                         msg=msg2+msg_git)
        self.assertEqual(self.fresh_mdb.metadata['test']['dumper'], 'self')
        self.assertEqual(self.fresh_mdb.metadata['test2']['dumper'], 'to_pickle')
        self.assertEqual(self.fresh_mdb.metadata['test']['metadata_creation_time'], \
                         'together_with_new_key')
        self.assertEqual(self.fresh_mdb.metadata['test2']['metadata_creation_time'], \
                         'together_with_new_key')
         
        # directly after deleting metadata database, every information is "unknown"
        metadata_db_path = os.path.join(self.path_fresh_mdb, 'metadata.db')
        assert(os.path.exists(metadata_db_path))
        os.remove(os.path.join(self.path_fresh_mdb, 'metadata.db')) 
         
        self.assertEqual(self.fresh_mdb.metadata['test']['dumper'], 'unknown')
        self.assertEqual(self.fresh_mdb.metadata['test2']['dumper'], 'unknown')
         
        #after initialization, the metdata is rebuild
        mdb = ModelDataBase(self.path_fresh_mdb)
        self.assertEqual(mdb.metadata['test']['version'], "unknown")
        self.assertEqual(mdb.metadata['test2']['version'], "unknown")
        self.assertEqual(mdb.metadata['test']['dumper'], 'self')
        self.assertEqual(mdb.metadata['test2']['dumper'], 'to_pickle')
        self.assertEqual(mdb.metadata['test']['metadata_creation_time'], \
                         'post_hoc')
        self.assertEqual(mdb.metadata['test2']['metadata_creation_time'], \
                         'post_hoc')        
 
    def test_check_working_dir_clean_for_build_works_correctly(self):
        #can create database in empty folder
        testpath = tempfile.mkdtemp()
        ModelDataBase(testpath)
         
        #cannot create database if file is in folder
        with open(os.path.join(testpath, 'somefile'), 'w'):
            pass
        self.assertRaises(Exception, ModelDataBase(testpath))
         
        #can create database if folder can be created but does not exist
        shutil.rmtree(testpath)
        ModelDataBase(testpath)
 
        #cannot create database if subfolder is in folder
        shutil.rmtree(testpath)
        os.makedirs(os.path.join(testpath, 'somefolder'))
        self.assertRaises(MdbException, lambda: ModelDataBase(testpath))
         
        #tidy up
        shutil.rmtree(testpath)
         
     
    def test_mdb_does_not_permit_writes_if_readonly(self):
        mdb = ModelDataBase(self.path_fresh_mdb, readonly = True)
        def fun():
            mdb['test'] = 1
        self.assertRaises(MdbException, fun)
     
    def test_mdb_will_not_be_created_if_nocreate(self):
        testpath = tempfile.mkdtemp()
        self.assertRaises(MdbException, lambda: ModelDataBase(testpath, nocreate=True))
        ModelDataBase(self.path_fresh_mdb, nocreate = True)
        shutil.rmtree(testpath)
             
    def test_managed_folder_really_exists(self):
        self.fresh_mdb.create_managed_folder('asd')
        self.assertTrue(os.path.exists(self.fresh_mdb['asd']))
         
        #deleting the db entry deletes the folder
        folder_path = self.fresh_mdb['asd']
        del self.fresh_mdb['asd']
        self.assertFalse(os.path.exists(folder_path))
     
    def test_managed_folder_does_not_overwrite_existing_keys(self):
        self.fresh_mdb.create_managed_folder('asd')
        self.assertRaises(MdbException, lambda: self.fresh_mdb.create_managed_folder('asd'))
     
    def test_can_instantiate_sub_mdb(self):
        self.fresh_mdb.create_sub_mdb('test_sub_mdb')
        self.assertIsInstance(self.fresh_mdb['test_sub_mdb'], ModelDataBase)
         
    def test_cannot_set_hierarchical_key_it_is_already_used_in_hierarchy(self):
        self.fresh_mdb['A'] = 1
        self.fresh_mdb[('B', '1')] = 2
        def fun(): self.fresh_mdb['A', '1'] = 1
        def fun2(): self.fresh_mdb['B'] = 1
        def fun3(): self.fresh_mdb['B', '1'] = 1
        def fun4(): self.fresh_mdb['B', '1', '2'] = 1
        self.assertRaises(MdbException, fun)
        self.assertRaises(MdbException, fun2)
        fun3()
        self.assertRaises(MdbException, fun4)     
     
    def test_keys_of_sub_mdbs_can_be_called_with_a_single_tuple(self):
        sub_mdb = self.fresh_mdb.create_sub_mdb(('A', '1'))
        sub_mdb['B'] = 1
        sub_mdb['C', '1'] = 2
        self.assertEqual(self.fresh_mdb['A','1','B'], 1)
        self.assertEqual(self.fresh_mdb['A','1','C', '1'], 2)
         
    def test_sub_mdb_does_not_overwrite_existing_keys(self):
        self.fresh_mdb.setitem('asd', 1)
        self.assertRaises(MdbException, lambda: self.fresh_mdb.create_sub_mdb('asd'))
     
    def test_can_set_items_using_different_dumpers(self):
        self.fresh_mdb.setitem('test_self', 1, dumper = 'self')
        self.fresh_mdb.setitem('test_to_pickle', 1, dumper = to_pickle)
        self.assertEqual(self.fresh_mdb['test_self'], \
                         self.fresh_mdb['test_to_pickle'])
     
    def test_setitem_allows_replacing_an_existing_key_while_simultaneously_using_it(self):
        self.fresh_mdb['test'] = 1
        self.fresh_mdb['test'] = self.fresh_mdb['test']+1
        self.assertEqual(self.fresh_mdb['test'], 2)
         
    def test_deleting_an_item_really_deletes_it(self):
        self.fresh_mdb['test'] = 1
        del self.fresh_mdb['test']
        assert len(list(self.fresh_mdb.keys())) == 0
         
    def test_overwriting_an_item_deletes_old_version(self):
        def count_number_of_subfolders(key):
            '''counts the number of folders that are in the mdb
            basedir that match a given key'''
            folders = [f for f in os.listdir(self.fresh_mdb.basedir) if key in f]
            return len(folders)
         
        self.assertEqual(count_number_of_subfolders('test'), 0)
        self.fresh_mdb['test'] = 1
        self.assertEqual(count_number_of_subfolders('test'), 1)
        self.fresh_mdb['test'] = 1
        self.assertEqual(count_number_of_subfolders('test'), 1)
        del self.fresh_mdb['test']
        self.assertEqual(count_number_of_subfolders('test'), 0)
         
    def test_maybe_calculate_runs_calculation_the_first_time_and_gets_result_from_mdb_afterwards(self):
        flag = []
        def fun():
            flag.append('fun_was_called')
            return 1
        res = self.fresh_mdb.maybe_calculate('my_key_where_result_of_fun_should_be_stored', fun)
        self.assertEqual(res, 1)
        self.assertEqual(len(list(self.fresh_mdb.keys())), 1)
        self.assertEqual(len(flag), 1)
        res = self.fresh_mdb.maybe_calculate('my_key_where_result_of_fun_should_be_stored', fun)
        self.assertEqual(res, 1)
        self.assertEqual(len(list(self.fresh_mdb.keys())), 1)
        self.assertEqual(len(flag), 1)
        fun()
        self.assertEqual(len(flag), 2)
         
    def test_accessing_non_existent_key_raises_KeyError(self):
        self.assertRaises(KeyError, lambda: self.fresh_mdb['some_nonexistent_key'])
    
    @decorators.testlevel(1)
    def test_compare_old_mdb_with_freshly_initialized_one(self):
        '''ensure compatibility with old versions'''
        old_path = os.path.join(parent, \
                                'test_model_data_base', \
                                'data',\
                                'already_initialized_mdb_for_compatibility_testing')
        old_mdb = ModelDataBase(old_path, \
                                readonly = True, \
                                nocreate = True)
        #old_mdb['reduced_model']
        
        with FreshlyInitializedMdb() as fmdb:
            assert_frame_equal(fmdb['voltage_traces'].compute(), \
                               fmdb['voltage_traces'].compute())
            assert_frame_equal(fmdb['synapse_activation'].compute(), \
                               fmdb['synapse_activation'].compute())
            assert_frame_equal(fmdb['cell_activation'].compute(), \
                               fmdb['cell_activation'].compute())
            assert_frame_equal(fmdb['metadata'], \
                               fmdb['metadata'])
            
        # reduced model can be loaded - commented out by Rieke during python 2to3 transition
#         Rm = old_mdb['reduced_lda_model']
#         Rm.plot() # to make sure, this can be called
                        
    def test_check_if_key_exists_can_handle_str_and_tuple_keys(self):
        self.fresh_mdb['a'] = 1
        self.fresh_mdb['b', 'b'] = 1
        self.assertTrue(self.fresh_mdb.check_if_key_exists('a'))
        self.assertTrue(self.fresh_mdb.check_if_key_exists(('a',)))   
        self.assertTrue(self.fresh_mdb.check_if_key_exists(('b', 'b')))
        self.assertFalse(self.fresh_mdb.check_if_key_exists(('a', 'b')))  
        self.assertFalse(self.fresh_mdb.check_if_key_exists('b'))
        
    def test_dumper_can_be_updated_and_metadata_is_adapted(self):
        self.fresh_mdb.setitem('a', 1, dumper = 'self')
        m = self.fresh_mdb.metadata['a']        
        self.assertTrue(m['dumper'] =='self')                
        self.fresh_mdb.change_dumper('a', to_pickle)
        m = self.fresh_mdb.metadata['a']
        self.assertTrue(m['dumper'] =='to_pickle')        
        self.assertTrue('dumper_update' in list(m.keys()))
        du = m['dumper_update']
        self.assertTrue(du[1]['dumper'] == 'to_pickle')