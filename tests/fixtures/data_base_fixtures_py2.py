import os, shutil, pytest, tempfile
from data_base.db_initializers.load_simrun_general import init
from data_base.model_data_base.mdb_initializers.load_simrun_general import init as init_mdb
from data_base.utils import silence_stdout
from data_base.data_base import DataBase
from data_base.model_data_base import ModelDataBase
from data_base.IO.LoaderDumper import pandas_to_msgpack
from data_base.model_data_base.IO.LoaderDumper import pandas_to_msgpack as mdb_pandas_to_msgpack
from ..context import TEST_DATA_FOLDER


# Py2 needs msgpack dumper, as parquet was not yet implemented for pandas DataFrames
@pytest.yield_fixture
def fresh_db():
    """Pytest fixture for a ModelDataBase object with a unique temp path.
    Initializes data with data_base.db_initializers.load_simrun_general.init
    Contains 8 keys with data:
    1. simresult_path
    2. filelist
    3. sim_trial_index
    4. metadata
    5. voltage_traces
    6. synapse_activation
    7. cell_activation
    8. spike_times

    Yields:
        data_base.DataBase: An db with data
    """
    # unique temp path
    path = tempfile.mkdtemp()
    db = DataBase(path)
    #self.db.settings.show_computation_progress = False

    with silence_stdout:
        init(
            db,
            TEST_DATA_FOLDER,
            rewrite_in_optimized_format=False,
            parameterfiles=False,
            dendritic_voltage_traces=False,
            dumper=pandas_to_msgpack)  # no Parquet dumper

    yield db
    # cleanup
    del db

@pytest.yield_fixture
def fresh_mdb():
    """Pytest fixture for a ModelDataBase object with a unique temp path.
    Initializes data with data_base.db_initializers.load_simrun_general.init
    Contains 8 keys with data:
    1. simresult_path
    2. filelist
    3. sim_trial_index
    4. metadata
    5. voltage_traces
    6. synapse_activation
    7. cell_activation
    8. spike_times

    Yields:
        data_base.ModelDataBase: An db with data
    """
    # unique temp path
    path = tempfile.mkdtemp()
    mdb = ModelDataBase(path)
    #self.db.settings.show_computation_progress = False

    with silence_stdout:
        init_mdb(
            mdb,
            TEST_DATA_FOLDER,
            rewrite_in_optimized_format=False,
            parameterfiles=False,
            dendritic_voltage_traces=False,
            dumper=mdb_pandas_to_msgpack)  # no Parquet dumper

    yield mdb
    # cleanup
    del mdb
    shutil.rmtree(path)

@pytest.yield_fixture
def empty_db():
    """Pytest fixture for a ModelDataBase object with a unique temp path.
    Does not initialize data, in contrast to fresh_db

    Yields:
        data_base.ModelDataBase: An empty db
        data_base.DataBase: An empty db
    """
    # unique temp path
    path = tempfile.mkdtemp()
    db = DataBase(path)

    yield db
    # cleanup
    del db

@pytest.yield_fixture
def empty_mdb():
    """Pytest fixture for a ModelDataBase object with a unique temp path.
    Does not initialize data, in contrast to fresh_db

    Yields:
        data_base.ModelDataBase: An empty db
    """
    # unique temp path
    path = tempfile.mkdtemp()
    db = ModelDataBase(path)

    yield db
    # cleanup
    del db
    shutil.rmtree(path)

@pytest.yield_fixture
def sqlite_db():
    from data_base.sqlite_backend.sqlite_backend import SQLiteBackend as SqliteDict
    tempdir = tempfile.mkdtemp()
    path = os.path.join(tempdir, 'tuplecloudsql_test.db')
    db = SqliteDict(path)

    yield db
    # cleanup
    if os.path.exists(tempdir):
        shutil.rmtree(tempdir)