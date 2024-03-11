from data_base.data_base import DataBase
from data_base import data_base_register, DataBaseException
from data_base.data_base import get_versions
import data_base.IO.LoaderDumper.to_pickle as to_pickle
from data_base.IO.LoaderDumper import pandas_to_msgpack
import pytest, os, shutil, six, tempfile, warnings, subprocess
import numpy as np
from getting_started import parent as getting_started_parent
import pandas
from pandas.util.testing import assert_frame_equal
from data_base.db_initializers.load_simrun_general import init
from data_base.utils import silence_stdout
from data_base import IO

parent = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def test_unique_id_is_set_on_initialization(empty_db):
    assert empty_db._unique_id is not None


def test_unique_id_stays_the_same_on_reload(empty_db):
    db1 = empty_db
    db2 = DataBase(empty_db.basedir)
    assert db1._unique_id == db2._unique_id


def test_new_unique_id_is_generated_if_it_is_not_set_yet(empty_db):
    empty_db._unique_id = None
    empty_db.save_db_state()
    assert empty_db._unique_id is None
    db = DataBase(empty_db.basedir)
    assert db._unique_id is not None


def test_get_dumper_string_by_dumper_module(empty_db):
    '''dumper string should be the modules name wrt IO.LoaderDumpers'''
    s1 = IO.LoaderDumper.get_dumper_string_by_dumper_module(to_pickle)
    s2 = 'to_pickle'
    assert s1 == s2


def test_get_dumper_string_by_savedir(empty_db):
    '''dumper string should be the same if it is determined
    post hoc (by providing the path to an already existing folder)
    or from the module reference directly.'''
    empty_db.set('test', 1, dumper=to_pickle)
    s1 = empty_db._detect_dumper_string_of_existing_key('test')
    s2 = IO.LoaderDumper.get_dumper_string_by_dumper_module(to_pickle)
    assert s1 == s2


def test_can_detect_default_dumper(empty_db):
    '''dumper string should be the same if it is determined
    post hoc (by providing the path to an already existing folder)
    or from the module reference directly.'''
    empty_db.set('test', 1)  # don't specify dumper
    s1 = empty_db._detect_dumper_string_of_existing_key('test')
    assert s1 == 'to_cloudpickle'


def test_metadata_update(empty_db):
    '''the method _update_metadata_if_necessary has the purpose of
    providing a smooth transition from databases, that had not implemented
    metadata to the newer version. This function should not overwrite
    existing metadata'''
    empty_db.set('test', 1)
    empty_db.set('test2', 1, dumper=to_pickle)
    msg1 = "{} =/= {}".format(empty_db.metadata['test']['version'],
                              get_versions()['version'])
    msg2 = "{} =/= {}".format(empty_db.metadata['test2']['version'],
                              get_versions()['version'])
    msg_git = "\nDid the commit turn dirty during testing?\n"
    msg_git += subprocess.check_output(['git status'],
                                       shell=True).decode('utf-8')
    assert empty_db.metadata['test']['version'] == get_versions(
    )['version'], msg1 + msg_git
    assert empty_db.metadata['test2']['version'] == get_versions(
    )['version'], msg2 + msg_git
    assert empty_db.metadata['test']['dumper'], 'to_cloudpickle'
    assert empty_db.metadata['test2']['dumper'] == 'to_pickle'
    assert empty_db.metadata['test'][
        'metadata_creation_time'] == 'together_with_new_key'
    assert empty_db.metadata['test2'][
        'metadata_creation_time'] == 'together_with_new_key'

    # directly after deleting metadata database, every information is "unknown"
    metadata_db_path = os.path.join(empty_db.basedir, 'test', 'metadata.json')
    assert os.path.exists(metadata_db_path)
    os.remove(metadata_db_path)
    metadata_db_path = os.path.join(empty_db.basedir, 'test2', 'metadata.json')
    assert os.path.exists(metadata_db_path)
    os.remove(metadata_db_path)

    assert empty_db.metadata['test']['dumper'] == 'unknown'
    assert empty_db.metadata['test2']['dumper'] == 'unknown'

    #after initialization, the metdata is rebuild
    db = DataBase(empty_db.basedir)
    assert db.metadata['test']['version'], "unknown"
    assert db.metadata['test2']['version'] == "unknown"
    assert db.metadata['test']['dumper'] == 'to_cloudpickle'
    assert db.metadata['test2']['dumper'] == 'to_pickle'
    assert db.metadata['test']['metadata_creation_time'] == 'post_hoc'
    assert db.metadata['test2']['metadata_creation_time'] == 'post_hoc'


def test_check_working_dir_clean_for_build_works_correctly():
    #can create database in empty folder
    testpath = tempfile.mkdtemp()

    #cannot create database if file is in folder
    with open(os.path.join(testpath, 'somefile'), 'w'):
        pass
    with pytest.raises(DataBaseException):
        DataBase(testpath)

    #can create database if folder can be created but does not exist
    shutil.rmtree(testpath)
    DataBase(testpath)

    #cannot create database if subfolder is in folder
    shutil.rmtree(testpath)
    os.makedirs(os.path.join(testpath, 'somefolder'))
    with pytest.raises(Exception):
        DataBase(testpath)

    #tidy up
    shutil.rmtree(testpath)


def test_db_does_not_permit_writes_if_readonly(empty_db):
    db = empty_db
    db.readonly = True

    def fun():
        db['test'] = 1

    with pytest.raises(DataBaseException):
        fun()


def test_db_will_not_be_created_if_nocreate(empty_db):
    testpath = tempfile.mkdtemp()
    with pytest.raises(Exception):
        DataBase(testpath, nocreate=True)
    DataBase(empty_db.basedir, nocreate=True)
    shutil.rmtree(testpath)


def test_managed_folder_really_exists(empty_db):
    empty_db.create_managed_folder('asd')
    assert os.path.exists(empty_db['asd'])

    #deleting the db entry deletes the folder
    folder_path = empty_db['asd']
    del empty_db['asd']
    assert not os.path.exists(folder_path)


def test_managed_folder_does_not_overwrite_existing_keys(empty_db):
    empty_db.create_managed_folder('asd')
    with pytest.raises(DataBaseException):
        empty_db.create_managed_folder('asd')


def test_can_instantiate_sub_db(empty_db):
    empty_db.create_sub_db('test_sub_db')
    assert isinstance(empty_db['test_sub_db'], DataBase)


def test_cannot_set_hierarchical_key_it_is_already_used_in_hierarchy(empty_db):
    empty_db['A'] = 1
    empty_db[('B', '1')] = 2

    def fun():
        empty_db['A', '1'] = 1

    def fun2():
        empty_db['B'] = 1

    def fun3():
        empty_db['B', '1'] = 1

    def fun4():
        empty_db['B', '1', '2'] = 1

    with pytest.raises(DataBaseException):
        fun()
    with pytest.raises(DataBaseException):
        fun2()
    fun3()
    with pytest.raises(DataBaseException):
        fun4()


def test_keys_of_sub_dbs_can_be_called_with_a_single_tuple(empty_db):
    sub_db = empty_db.create_sub_db(('A', '1'))
    sub_db['B'] = 1
    sub_db['C', '1'] = 2
    assert empty_db['A', '1', 'B'] == 1
    assert empty_db['A', '1', 'C', '1'] == 2


def test_sub_db_does_not_overwrite_existing_keys(empty_db):
    empty_db.set('asd', 1)
    with pytest.raises(DataBaseException):
        empty_db.create_sub_db('asd')


def test_can_set_items_using_different_dumpers(empty_db):
    empty_db.set('test_self', 1)
    empty_db.set('test_to_pickle', 1, dumper=to_pickle)
    assert empty_db['test_self'] == empty_db['test_to_pickle']


def test_setitem_allows_replacing_an_existing_key_while_simultaneously_using_it(
        empty_db):
    empty_db['test'] = 1
    empty_db['test'] = empty_db['test'] + 1
    assert empty_db['test'] == 2


def test_deleting_an_item_really_deletes_it(empty_db):
    empty_db['test'] = 1
    del empty_db['test']
    assert len(list(empty_db.keys())) == 0


def test_overwriting_an_item_deletes_old_version(empty_db):

    def count_number_of_subfolders(key):
        '''counts the number of folders that are in the db
        basedir that match a given key'''
        folders = [f for f in os.listdir(empty_db.basedir) if key in f and not ".deleting." in f]
        return len(folders)

    assert count_number_of_subfolders('test') == 0
    empty_db['test'] = 1
    assert count_number_of_subfolders('test') == 1
    empty_db['test'] = 1
    assert count_number_of_subfolders('test') == 1
    del empty_db['test']
    assert count_number_of_subfolders('test') == 0


def test_maybe_calculate_runs_calculation_the_first_time_and_gets_result_from_db_afterwards(
        empty_db):
    db = empty_db
    flag = []

    def fun():
        flag.append('fun_was_called')
        return 1

    res = empty_db.maybe_calculate(
        'my_key_where_result_of_fun_should_be_stored', fun)
    assert res == 1
    assert len(list(empty_db.keys())) == 1
    assert len(flag) == 1
    res = empty_db.maybe_calculate(
        'my_key_where_result_of_fun_should_be_stored', fun)
    assert res == 1
    assert len(list(empty_db.keys())) == 1
    assert len(flag) == 1
    fun()
    assert len(flag) == 2


def test_accessing_non_existent_key_raises_KeyError(empty_db):
    with pytest.raises(KeyError):
        empty_db['some_nonexistent_key']


@pytest.mark.skipif(
    six.PY3,
    reason=
    "Old db only readable in Py2. Py3 does not have pandas.indexes. It has been moved to pandas.core.indexes."
)
def test_compare_old_db_with_freshly_initialized_one(client):
    '''ensure compatibility with old versions'''
    old_path = os.path.join(parent, \
                            'test_data_base', \
                            'data',\
                            'already_initialized_db_for_compatibility_testing')
    old_db = DataBase(old_path, readonly=True, nocreate=True)

    # Manually create db
    path = tempfile.mkdtemp()
    fresh_db = DataBase(path)
    test_data_folder = os.path.join(getting_started_parent,
                                    'example_simulation_data')
    with silence_stdout:
        init(fresh_db,
             test_data_folder,
             client=client,
             rewrite_in_optimized_format=False,
             parameterfiles=False,
             dendritic_voltage_traces=False,
             dumper = pandas_to_msgpack)

    #old_db['reduced_model']
    assert_frame_equal(fresh_db['voltage_traces'].compute().sort_index(axis=1), \
                        old_db['voltage_traces'].compute().sort_index(axis=1))
    assert_frame_equal(fresh_db['synapse_activation'].compute().sort_index(axis=1), \
                        old_db['synapse_activation'].compute().sort_index(axis=1))
    assert_frame_equal(fresh_db['cell_activation'].compute().sort_index(axis=1), \
                        old_db['cell_activation'].compute().sort_index(axis=1))
    assert_frame_equal(fresh_db['metadata'].sort_index(axis=1), \
                        old_db['metadata'].sort_index(axis=1))

    # cleanup
    shutil.rmtree(path)

    # reduced model can be loaded - commented out by Rieke during python 2to3 transition
    #     Rm = old_db['reduced_lda_model']
    #     Rm.plot() # to make sure, this can be called


def test_check_if_key_exists_can_handle_str_and_tuple_keys(empty_db):
    empty_db['a'] = 1
    empty_db['b', 'b'] = 1
    assert empty_db.check_if_key_exists('a')
    assert empty_db.check_if_key_exists(('a',))
    assert empty_db.check_if_key_exists(('b', 'b'))
    assert not empty_db.check_if_key_exists(('a', 'b'))
    assert empty_db.check_if_key_exists('b')
