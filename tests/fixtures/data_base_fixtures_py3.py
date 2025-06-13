import os, shutil, pytest, tempfile
from data_base.db_initializers.load_simrun_general import init
from data_base.utils import silence_stdout
from data_base.data_base import DataBase
from data_base.model_data_base import ModelDataBase
from ..context import TEST_DATA_FOLDER

@pytest.fixture
def fresh_db(worker_id):
    """Pytest fixture for an data_base.DataBase object with a unique temp path.
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
        data_base.DataBase: A db with data
    """
    # unique temp path
    path = tempfile.mkdtemp(prefix=worker_id)
    db = DataBase(path)
    #self.db.settings.show_computation_progress = False

    with silence_stdout:
        init(
            db,
            TEST_DATA_FOLDER,
            rewrite_in_optimized_format=False,
            parameterfiles=False,
            dendritic_voltage_traces=False)

    yield db
    # cleanup
    # db.remove()
    # del db

@pytest.fixture
def empty_db(worker_id):
    """Pytest fixture for a DataBase object with a unique temp path.
    Does not initialize data, in contrast to fresh_db

    Yields:
        data_base.DataBase: An empty db
    """
    # unique temp path
    path = tempfile.mkdtemp(prefix=worker_id)
    db = DataBase(path)

    yield db
    # cleanup
    for key in db.keys():
        del key
    # db.remove()
    # del db

@pytest.fixture
def sqlite_db():
    from data_base.sqlite_backend.sqlite_backend import SQLiteBackend as SqliteDict
    tempdir = tempfile.mkdtemp()
    path = os.path.join(tempdir, 'tuplecloudsql_test.db')
    db = SqliteDict(path)

    yield db
    # cleanup
    if os.path.exists(tempdir):
        shutil.rmtree(tempdir)