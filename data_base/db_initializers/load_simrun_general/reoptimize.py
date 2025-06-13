"""Re-optimize a database with a new dumper

Database optimization involves writing out various dataframes in a so-called `"optimized"` format.
It is sometimes of interest to re-write an already optimized database with a new (or old) data format.
For example, in the past we have switched from `msgpack` to `parquet`, and back to `msgpack` after un-deprecating it. 
So all databases optimized with `parquet` could now in principle be re-optimized with `msgpack`.
"""

from data_base.data_base import is_sub_data_base
from data_base.exceptions import DataBaseException
from data_base.data_base import _is_legacy_model_data_base
from .utils import _get_dumper
import importlib
import shutil, os, random
import dask.dataframe as dd
import logging
from tqdm import tqdm
from .config import DUMPERS_TO_REOPTIMIZE

isf_logger = logging.getLogger("ISF")
logger = isf_logger.getChild(__name__)

def _check_needs_reoptimization(key, old_dumper_name, new_dumper_name):
    """Check if a key needs re-optimization.
    
    Dumper formats that need to be re-optimized are saved in :py:mod:`~data_base.db_initializers.load_simrun_general.config`.
    
    Args:
        key (str): The key to check.
        old_dumper_name (str): The name of the old dumper.
        new_dumper_name (str): The name of the new dumper.
        
    Returns:
        bool: True if the key needs re-optimization, False otherwise.
    
    Raises:
        DataBaseException: If the key is not in the database.
        
    Raises:
        Warning: If the old and new dumper are configured to be the same (should not be the case).
    """
    if new_dumper_name == old_dumper_name:
        logger.warning("I am configured to re-optimize the dumper `{}`, but the current default optimized dumper for `{}` is also `{}`. Skipping this key...".format(
            old_dumper_name, key, new_dumper_name))
        return False
    else:
        logger.debug("Reoptimizing `{}` from `{}` to `{}`".format(key, old_dumper_name, new_dumper_name))
        return True


def _get_dumper_kwargs(d, client=None):
    """Get the dumper kwargs for a given DataFrame.
    
    This is used to determine if saving the dataframe requires a client or not.
    
    :skip-doc:
    """
    if isinstance(d, dd.DataFrame):
        assert client is not None, "Please provide a dask client to re-optimize the database."
        return {"client": client}
    else:
        return {}

        
def _reoptimize_key(db, key, new_dumper, client=None):
    # Find the path to the key
    # can't use wrapper API here, since mdb's will be constructed by the LoaderDumper, which explicitly points to the Mdb class
    if _is_legacy_model_data_base(db.basedir):
        path_to_key = db._get_path(key)
    else:
        path_to_key = db._convert_key_to_path(key)
    temp_key = key+"_{}_reoptimizing".format(random.randint(0, 100000))
    temp_path = os.path.join(db.basedir, temp_key)

    try:    
        logger.debug("Temporarily moving `{}` to `{}`".format(path_to_key, temp_path))
        shutil.move(path_to_key, temp_path)  # move original key to tmp location

        if hasattr(db, "_sql_backend"):  # mdb compat
            dummy = db._sql_backend[key]
            dummy.relpath = temp_path
            db._sql_backend[temp_key] = dummy
    
        d = db[temp_key]
        kwargs = _get_dumper_kwargs(d, client=client)
        logger.debug("Saving `{}` with new dumper `{}`".format(key, new_dumper.__name__))
        db.set(key, d, dumper=new_dumper, **kwargs)
        logger.debug("Removing temporary key `{}`".format(temp_key))
        shutil.rmtree(temp_path)
    except Exception as e:
        if os.path.exists(path_to_key):
            shutil.rmtree(path_to_key)  
        shutil.move(temp_path, path_to_key)
        raise DataBaseException(f"Failed to re-optimize {key}") from e
    finally:
        if hasattr(db, "_sql_backend"):
            del db._sql_backend[temp_key]


def reoptimize_db(db, client=None, progress=False, n_db_parents=0, suppress_warnings=False):
    """Re-optimize a database with a new dumper.
    
    This function will re-optimize all keys in the database that are configured to be re-optimized.
    This is useful for switching between different data formats, such as from `parquet` to `msgpack`.
    
    It recurses into subdatabases, and re-optimizes them as well.
    
    Args:
        db (:py:mod:`~data_base.data_base.isf_data_base.ISFDataBase`): 
            The database to re-optimize.
        client (dask.distributed.Client):
            The dask client to use for re-optimizing the database.
        progress (bool):
            If True, show a progress bar for the re-optimization.
            Subdatabases have nested progress bars.
            It is recommended to also suppress warnings when using progress bars, so
            the output stays readable.
        suppress_warnings (bool):
            If True, suppress warnings during re-optimization.
            
    Returns:
        None
    """
    assert client is not None, "Please provide a dask client to re-optimize the database."
    logger.info("Reoptimizing database at {}".format(db.basedir))
    keys = db.keys() 
    if progress:
        if n_db_parents == 0: db_name = os.path.basename(db.basedir)
        else: db_name = os.path.basename(os.path.dirname(db.basedir))
        keys = tqdm(
            keys, 
            desc="Reoptimizing {}".format(db_name), 
            position=n_db_parents, 
            leave=False)
    original_level = isf_logger.level
    if suppress_warnings: isf_logger.setLevel(logging.ERROR)

    try:
        for key in keys:
            logger.debug("Checking key `{}`".format(key))
            if is_sub_data_base(db, key):
                logger.info("Reoptimizing subdatabase {}".format(key))
                reoptimize_db(db[key], client=client, n_db_parents=n_db_parents+1, progress=progress)
                continue
            elif db.metadata[key]['dumper'] in DUMPERS_TO_REOPTIMIZE:
                is_categorizable = key in ("cell_activation", "synapse_activation")
                new_dumper = _get_dumper(db[key], categorized=is_categorizable)
                old_dumper_name = db.metadata[key]['dumper']
                if _is_legacy_model_data_base(db.basedir):
                    new_dumper = importlib.import_module(new_dumper.__name__.replace("isf_data_base", "model_data_base"))
                
                if not _check_needs_reoptimization(key, old_dumper_name, new_dumper.__name__):
                    logger.debug("Skipping `{}` because it does not need re-optimization".format(key))
                    continue
                
                try:
                    logger.debug("Reoptimizing `{}` with new dumper `{}`".format(key, new_dumper.__name__))
                    _reoptimize_key(db, key, new_dumper, client=client)
                except Exception as e:
                    raise DataBaseException(f"Failed to re-optimize {key}") from e
    finally:
        if suppress_warnings:
            isf_logger.setLevel(original_level)
