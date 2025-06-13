
import os, sys, importlib
import config, data_base

def _set_isf_use_mdb(val="0"):
    os.environ["ISF_USE_MDB"] = val
    # clean context
    _reload_modules()
    # Remove python-cached modules to ensure they are reloaded
    del data_base.IO

def test_switch_db_backend(tmpdir):
    """
    Test if you can switch between ISF Data Base and Model Data Base
    using the ISF_USE_MDB environment variable.
    """

    # Save the original value of the environment variable
    original_env_value = os.environ.get("ISF_USE_MDB")
    tmp_db_path = os.path.join(tmpdir, "test_db")
    tmp_mdb_path = os.path.join(tmpdir, "test_mdb")

    try:
        _set_isf_use_mdb("0")  # Set to "0" (use ISF Data Base)
        assert config.isf_is_using_mdb() == False, "Expected ISF_USE_MDB to be False"
        db = data_base.DataBase(tmp_db_path)
        assert isinstance(db, data_base.isf_data_base.ISFDataBase), "Database is not of type ISFDataBase"
        from data_base import IO
        assert IO.__name__.startswith("data_base.isf_data_base.IO"), \
            f"Wrong IO package imported. Expected 'data_base.isf_data_base.IO', but got '{IO.__name__}'"

        # Test with ISF_USE_MDB set to "1" (use Model Data Base)
        _set_isf_use_mdb("1")
        assert config.isf_is_using_mdb() == True, "Expected ISF_USE_MDB to be True"
        db = data_base.DataBase(tmp_mdb_path)
        assert isinstance(db, data_base.model_data_base.ModelDataBase), "Database is not of type ModelDataBase"
        from data_base import IO
        assert IO.__name__.startswith("data_base.model_data_base.IO"), \
            f"Wrong IO package imported. Expected 'data_base.model_data_base.IO', but got '{IO.__name__}'"

    finally:
        # Restore the original value of the environment variable
        if original_env_value is not None:
            os.environ["ISF_USE_MDB"] = original_env_value
        else:
            del os.environ["ISF_USE_MDB"]

def _reload_modules():
    """
    Helper function to reload modules after changing the environment variable.
    """
    # Remove cached modules to ensure they are reloaded
    for module in list(sys.modules):
        if module.startswith("data_base.IO"):
            del sys.modules[module]
    importlib.reload(config)  # Reload config to pick up the updated environment variable
    importlib.reload(data_base)  # Reload data_base to reinitialize with the correct IO package
