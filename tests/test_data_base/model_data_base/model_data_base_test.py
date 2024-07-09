from data_base.model_data_base.model_data_base import ModelDataBase, MdbException
from data_base._version import get_versions
from data_base.model_data_base.IO.LoaderDumper import pandas_to_msgpack, to_pickle
import pytest, os, shutil, six, tempfile, subprocess
from getting_started import parent as getting_started_parent
from pandas.util.testing import assert_frame_equal
from data_base.model_data_base.mdb_initializers.load_simrun_general import init
from data_base.utils import silence_stdout
from data_base.model_data_base import IO

parent = os.path.abspath(os.path.dirname(__file__))


def test_unique_id_is_set_on_initialization(empty_mdb):
    assert empty_mdb._unique_id is not None


def test_unique_id_stays_the_same_on_reload(empty_mdb):
    db1 = empty_mdb
    db2 = ModelDataBase(empty_mdb.basedir)
    assert db1._unique_id == db2._unique_id


def test_new_unique_id_is_generated_if_it_is_not_set_yet(empty_mdb):
    empty_mdb._unique_id = None
    empty_mdb.save_mdb()
    assert empty_mdb._unique_id is None
    mdb = ModelDataBase(empty_mdb.basedir)
    assert mdb._unique_id is not None


def test_get_dumper_string_by_dumper_module():
    '''dumper string should be the modules name wrt IO.LoaderDumpers'''
    s1 = IO.LoaderDumper.get_dumper_string_by_dumper_module(to_pickle)
    s2 = 'to_pickle'
    assert s1 == s2


def test_get_dumper_string_by_savedir(empty_mdb):
    '''dumper string should be the same if it is determined
    post hoc (by providing the path to an already existing folder)
    or from the module reference directly.'''
    empty_mdb.setitem('test', 1, dumper=to_pickle)
    s1 = empty_mdb._detect_dumper_string_of_existing_key('test')
    s2 = IO.LoaderDumper.get_dumper_string_by_dumper_module(to_pickle)
    assert s1 == s2


def test_can_detect_default_dumper(empty_mdb):
    '''dumper string should be the same if it is determined
    post hoc (by providing the path to an already existing folder)
    or from the module reference directly.'''
    empty_mdb.setitem('test', 1)  # don't specify dumper
    s1 = empty_mdb._detect_dumper_string_of_existing_key('test')
    assert s1 == 'to_cloudpickle'


def test_metadata_update(empty_mdb):
    '''the method _update_metadata_if_necessary has the purpose of
    providing a smooth transition from databases, that had not implemented
    metadata to the newer version. This function should not overwrite
    existing metadata'''
    empty_mdb.setitem('test', 1)
    empty_mdb.setitem('test2', 1, dumper=to_pickle)
    msg1 = "{} =/= {}".format(empty_mdb.metadata['test']['version'],
                              get_versions()['version'])
    msg2 = "{} =/= {}".format(empty_mdb.metadata['test2']['version'],
                              get_versions()['version'])
    msg_git = "\nDid the commit turn dirty during testing?\n"
    msg_git += subprocess.check_output(['git status'],
                                       shell=True).decode('utf-8')
    assert empty_mdb.metadata['test']['version'] == get_versions(
    )['version'], msg1 + msg_git
    assert empty_mdb.metadata['test2']['version'] == get_versions(
    )['version'], msg2 + msg_git
    assert empty_mdb.metadata['test']['dumper'], 'to_cloudpickle'
    assert empty_mdb.metadata['test2']['dumper'] == 'to_pickle'
    assert empty_mdb.metadata['test'][
        'metadata_creation_time'] == 'together_with_new_key'
    assert empty_mdb.metadata['test2'][
        'metadata_creation_time'] == 'together_with_new_key'

    # directly after deleting metadata database, every information is "unknown"
    metadata_db_path = os.path.join(empty_mdb.basedir, 'metadata.db')
    assert os.path.exists(metadata_db_path)
    os.remove(metadata_db_path)

    assert empty_mdb.metadata['test']['dumper'] == 'unknown'
    assert empty_mdb.metadata['test2']['dumper'] == 'unknown'

    #after initialization, the metdata is rebuild
    db = ModelDataBase(empty_mdb.basedir)
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
    with pytest.raises(MdbException):
        ModelDataBase(testpath)

    #can create database if folder can be created but does not exist
    shutil.rmtree(testpath)
    ModelDataBase(testpath)

    #cannot create database if subfolder is in folder
    shutil.rmtree(testpath)
    os.makedirs(os.path.join(testpath, 'somefolder'))
    with pytest.raises(Exception):
        ModelDataBase(testpath)

    #tidy up
    shutil.rmtree(testpath)


def test_db_does_not_permit_writes_if_readonly(empty_mdb):
    db = empty_mdb
    db.readonly = True

    def fun():
        db['test'] = 1

    with pytest.raises(MdbException):
        fun()


def test_db_will_not_be_created_if_nocreate(empty_mdb):
    testpath = tempfile.mkdtemp()
    with pytest.raises(Exception):
        ModelDataBase(testpath, nocreate=True)
    ModelDataBase(empty_mdb.basedir, nocreate=True)
    shutil.rmtree(testpath)


def test_managed_folder_really_exists(empty_mdb):
    empty_mdb.create_managed_folder('asd')
    assert os.path.exists(empty_mdb['asd'])

    #deleting the db entry deletes the folder
    folder_path = empty_mdb['asd']
    del empty_mdb['asd']
    assert not os.path.exists(folder_path)


def test_managed_folder_does_not_overwrite_existing_keys(empty_mdb):
    empty_mdb.create_managed_folder('asd')
    with pytest.raises(MdbException):
        empty_mdb.create_managed_folder('asd')


def test_can_instantiate_sub_mdb(empty_mdb):
    empty_mdb.create_sub_mdb('test_sub_mdb')
    assert isinstance(empty_mdb['test_sub_mdb'], ModelDataBase)


def test_cannot_set_hierarchical_key_it_is_already_used_in_hierarchy(empty_mdb):
    empty_mdb['A'] = 1
    empty_mdb[('B', '1')] = 2

    def fun():
        empty_mdb['A', '1'] = 1

    def fun2():
        empty_mdb['B'] = 1

    def fun3():
        empty_mdb['B', '1'] = 1

    def fun4():
        empty_mdb['B', '1', '2'] = 1

    with pytest.raises(MdbException):
        fun()
    with pytest.raises(MdbException):
        fun2()
    fun3()
    with pytest.raises(MdbException):
        fun4()


def test_keys_of_sub_mdbs_can_be_called_with_a_single_tuple(empty_mdb):
    sub_mdb = empty_mdb.create_sub_mdb(('A', '1'))
    sub_mdb['B'] = 1
    sub_mdb['C', '1'] = 2
    assert empty_mdb['A', '1', 'B'] == 1
    assert empty_mdb['A', '1', 'C', '1'] == 2


def test_sub_mdb_does_not_overwrite_existing_keys(empty_mdb):
    empty_mdb.setitem('asd', 1)
    with pytest.raises(MdbException):
        empty_mdb.create_sub_mdb('asd')


def test_can_set_items_using_different_dumpers(empty_mdb):
    empty_mdb.setitem('test_self', 1)
    empty_mdb.setitem('test_to_pickle', 1, dumper=to_pickle)
    assert empty_mdb['test_self'] == empty_mdb['test_to_pickle']


def test_setitem_allows_replacing_an_existing_key_while_simultaneously_using_it(
        empty_mdb):
    empty_mdb['test'] = 1
    empty_mdb['test'] = empty_mdb['test'] + 1
    assert empty_mdb['test'] == 2


def test_deleting_an_item_really_deletes_it(empty_mdb):
    empty_mdb['test'] = 1
    del empty_mdb['test']
    assert len(list(empty_mdb.keys())) == 0


def test_overwriting_an_item_deletes_old_version(empty_mdb):

    def count_number_of_subfolders(key):
        '''counts the number of folders that are in the db
        basedir that match a given key'''
        folders = [f for f in os.listdir(empty_mdb.basedir) if key in f and not ".deleting." in f]
        return len(folders)

    assert count_number_of_subfolders('test') == 0
    empty_mdb['test'] = 1
    assert count_number_of_subfolders('test') == 1
    empty_mdb['test'] = 1
    assert count_number_of_subfolders('test') == 1
    del empty_mdb['test']
    assert count_number_of_subfolders('test') == 0


def test_maybe_calculate_runs_calculation_the_first_time_and_gets_result_from_db_afterwards(
        empty_mdb):
    db = empty_mdb
    flag = []

    def fun():
        flag.append('fun_was_called')
        return 1

    res = empty_mdb.maybe_calculate(
        'my_key_where_result_of_fun_should_be_stored', fun)
    assert res == 1
    assert len(list(empty_mdb.keys())) == 1
    assert len(flag) == 1
    res = empty_mdb.maybe_calculate(
        'my_key_where_result_of_fun_should_be_stored', fun)
    assert res == 1
    assert len(list(empty_mdb.keys())) == 1
    assert len(flag) == 1
    fun()
    assert len(flag) == 2


def test_accessing_non_existent_key_raises_KeyError(empty_mdb):
    with pytest.raises(KeyError):
        empty_mdb['some_nonexistent_key']


@pytest.mark.skipif(
    six.PY3,
    reason=
    "Old db only readable in Py2. Py3 does not have pandas.indexes. It has been moved to pandas.core.indexes."
)
def test_compare_old_mdb_with_freshly_initialized_one(client):
    '''ensure compatibility with old versions'''
    old_path = os.path.join(
        parent, 
        'data',
        'already_initialized_mdb_for_compatibility_testing')
    old_db = ModelDataBase(old_path, readonly=True, nocreate=True)

    # Manually create db
    path = tempfile.mkdtemp()
    fresh_mdb = ModelDataBase(path)
    test_data_folder = os.path.join(
        getting_started_parent,
        'example_data',
        'simulation_data',
        )
    with silence_stdout:
        init(
            fresh_mdb,
            simresult_path=test_data_folder,
            client=client,
            rewrite_in_optimized_format=False,
            parameterfiles=False,
            dendritic_voltage_traces=False,
            dumper = pandas_to_msgpack)

    #old_db['reduced_model']
    assert_frame_equal(fresh_mdb['voltage_traces'].compute().sort_index(axis=1), \
                        old_db['voltage_traces'].compute().sort_index(axis=1))
    assert_frame_equal(fresh_mdb['synapse_activation'].compute().sort_index(axis=1), \
                        old_db['synapse_activation'].compute().sort_index(axis=1))
    assert_frame_equal(fresh_mdb['cell_activation'].compute().sort_index(axis=1), \
                        old_db['cell_activation'].compute().sort_index(axis=1))
    assert_frame_equal(fresh_mdb['metadata'].sort_index(axis=1), \
                        old_db['metadata'].sort_index(axis=1))

    # cleanup
    shutil.rmtree(path)


def test_check_if_key_exists_can_handle_str_and_tuple_keys(empty_mdb):
    empty_mdb['a'] = 1
    empty_mdb['b', 'b'] = 1
    assert empty_mdb.check_if_key_exists('a')
    assert empty_mdb.check_if_key_exists(('a',))
    assert empty_mdb.check_if_key_exists(('b', 'b'))
    assert not empty_mdb.check_if_key_exists(('a', 'b'))
    assert not empty_mdb.check_if_key_exists('b')
