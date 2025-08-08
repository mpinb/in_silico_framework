import glob, logging, os
import dask
import dask.dataframe as dd
import pandas as pd
import numpy as np

import single_cell_parser as scp
import single_cell_parser.analyze as sca
from itertools import compress
from data_base.dbopen import resolve_neup_reldb_paths
from data_base.IO.LoaderDumper import pandas_to_msgpack
from data_base.IO.roberts_formats import (
    read_pandas_cell_activation_from_roberts_format as read_ca,
)
from data_base.IO.roberts_formats import (
    read_pandas_synapse_activation_from_roberts_format as read_sa,
)
from data_base.utils import chunkIt, silence_stdout

from .data_parsing import (
    load_dendritic_voltage_traces,
    read_voltage_traces_by_filenames,
)
from .file_handling import get_max_commas, make_filelist, get_recsite_labels_from_dend_vt_filelist
from .metadata_utils import create_metadata, get_voltage_traces_divisions_by_metadata
from .param_file_parser import (
    parallel_resolve_and_copy_paramfiles_to_db,
    construct_param_filename_hashmap_df,
)
from .health import get_filter_healthy_simresult_dirs
from .config import (
    NETP_DIR,
    NEUP_DIR,
    HOC_DIR,
    SYN_DIR,
    CON_DIR,
    RECSITES_DIR,
    DEFAULT_DUMPER,
    DEND_VT_SPLIT_PER_RECSITE_ID
)
from config.isf_logging import logger


def _filter_filelist_by_health(filelist, simresult_path, client):
    """Filter out simulation results if they can't be reproduced due to missing files.
    
    Missing parameterfiles can happen when data is recovered incompletely. If a simualtion
    directory is missing synapse activation files, cell activation files, parameter files,
    or the parameter files have references to missing :ref:`syn_file_format`, :ref:`con_file_format`,
    :ref:`hoc_file_format` or recsite files, the resulting voltage traces are not reproducible.
    
    This function checks if this is the case, and filters out such results from :paramref:`filelist`
    
    Args:
        filelist (List): 
            List of voltage trace results, relative to :paramref:`simresult_path`. 
        simresult_path (str): Single path where all simulation results are stored.
        client (:py:class:`distributed.client.Client`): A parallellization client.

    Returns:
        List: A filelist of reproducible simulation results.
        
    Raises:
        ValueError: if no simulations in :paramref:`filelist` can be reproduced.
    """
    logger.info("Checking if simulation directories contain parameterfiles incomplete results")
    sim_dirs = [os.path.join(simresult_path, os.path.dirname(f)) for f in filelist]
    is_healthy_mask = get_filter_healthy_simresult_dirs(sim_dirs, client=client)
    for broken_sim in list(compress(sim_dirs, ~is_healthy_mask)):
        logger.debug(f"Incomplete result: {broken_sim}. Check logger output (potentially on a dask worker) for more info")
    # Filter the filelist based on boolean is_healthy_mask
    filelist = list(compress(filelist, is_healthy_mask))
    if len(filelist) == 0: raise ValueError("Filelist empty. Abort initialization.")
    return filelist


def _build_core(
    db, 
    repartition=None, 
    metadata_dumper=pandas_to_msgpack,
    check_health=False,
    client=None
    ):
    """Parse the essential simulation results and add it to :paramref:`db`.

    The following data is parsed and added to the database:

    - filelist: A dask dataframe containing the paths to all soma voltage trace files.
    - voltage_traces: A dask dataframe containing the soma voltage traces.
    - sim_trial_index: A dask series containing the indices of the simulation trials.
    - metadata: A dask dataframe containing metadata about the simulation trials. See :py:meth:`~data_base.db_initializers.load_simrun_general.metadata_utils.create_metadata` for more information.

    Args:
        db (:py:class:`~data_base.DataBase`): The database to which the data should be added.
        repartition (bool): If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
        metadata_dumper (function): Function to dump the metadata to disk. Default is :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.pandas_to_msgpack`.

    Returns:
        None
    """
    assert repartition is not None
    logger.info("--- Building data base core ---")
    logger.info("Core consists of: voltage_traces, metadata, filelist, sim_trial_index")

    # 1. Generate filelist and sim_trial_index
    # filelist contains the paths to all soma voltage trace files
    # sim_trial_index contains the parent directory of these, plus the run IDs per sim result folder
    logger.info("Building filelist ...")
    try: 
        filelist = make_filelist(db["simresult_path"], "vm_all_traces.csv")
    except ValueError: 
        filelist = make_filelist(db["simresult_path"], "vm_all_traces.npz")
    if check_health:
        logger.info("Checking if simulation directories contain parameterfiles incomplete results")
        filelist = _filter_filelist_by_health(filelist, db["simresult_path"], client)

    db["filelist"] = filelist

    # 2. Generate dask dataframe containing the voltagetraces
    logger.info("Collecting voltage trace locations...")
    # vt = read_voltage_traces_by_filenames(db['simresult_path'], db['file_list'])
    vt = read_voltage_traces_by_filenames(
        prefix=db["simresult_path"], 
        fnames=filelist, 
        repartition=repartition,
    )
    
    db.set("voltage_traces", vt, dumper=DEFAULT_DUMPER)
    
    # 3. Read out the sim_trial_index from the soma voltage traces dask dataframe
    logger.info("Building voltage traces and sim_trial_index ...")
    # Only now is the VT df actually being read in
    db["sim_trial_index"] = db["voltage_traces"].index.compute()
    
    if db['sim_trial_index'].size == 0:
        raise ValueError("No valid sim trials found in the specified directory ({}). Check if the logs report invalid results.".format(db['simresult_path']))

    # 4. Generate metadata dataframe out of sim_trial_indices
    logger.info("Building metadata ...")
    db.set("metadata", create_metadata(db), dumper=metadata_dumper)

    logger.info("Adding divisions to voltage traces dataframe and writing to disk")
    vt.divisions = get_voltage_traces_divisions_by_metadata(db["metadata"], repartition=repartition)
    db.set("voltage_traces", vt, dumper=DEFAULT_DUMPER)


def _build_synapse_activation(db, repartition=False, n_chunks=5000):
    """Parse the :ref:`syn_activation_format` and :ref:`spike_times_format` data.

    The synapse and presynaptic spike times data is added to the database under the keys
    ``synapse_activation`` and ``cell_activation`` respectively.

    Args:
        db (:py:class:`~data_base.DataBase`): The database to which the data should be added.
        repartition (bool): If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
        n_chunks (int): Number of chunks to split the data into. Default is 5000.

    Returns:
        None
    """

    def template(key, paths, file_reader_fun, dumper):
        logging.info("counting commas")
        max_commas = get_max_commas(paths) + 1
        # print max_commas
        logging.info("generate dataframe")
        path_sti_tuples = list(zip(paths, list(db["sim_trial_index"])))
        if repartition and len(paths) > 10000:
            path_sti_tuples = chunkIt(path_sti_tuples, n_chunks)
            delayeds = [
                file_reader_fun(list(zip(*x))[0], list(zip(*x))[1], max_commas)
                for x in path_sti_tuples
            ]
            divisions = [x[0][1] for x in path_sti_tuples] + [
                path_sti_tuples[-1][-1][1]
            ]
        else:
            delayeds = [
                file_reader_fun(p, sti, max_commas) for p, sti in path_sti_tuples
            ]
            divisions = [x[1] for x in path_sti_tuples] + [path_sti_tuples[-1][1]]
        ddf = dd.from_delayed(
            delayeds, meta=delayeds[0].compute(scheduler="threads"), divisions=divisions
        )
        logging.info("save dataframe")
        db.set(key, ddf, dumper=dumper)

    simresult_path = db["simresult_path"]
    if simresult_path[-1] == "/" and len(simresult_path) > 1:
        simresult_path = simresult_path[:-1]

    m = db["metadata"].reset_index()
    if "synapses_file_name" in m.columns:
        logging.info("---building synapse activation dataframe---")
        paths = list(simresult_path + "/" + m.path + "/" + m.synapses_file_name)
        template(
            "synapse_activation",
            paths,
            dask.delayed(read_sa, traverse=False),
            DEFAULT_DUMPER,
        )
    if "cells_file_name" in m.columns:
        logging.info("---building cell activation dataframe---")
        paths = list(simresult_path + "/" + m.path + "/" + m.cells_file_name)
        template(
            "cell_activation",
            paths,
            dask.delayed(read_ca, traverse=False),
            DEFAULT_DUMPER,
        )


def _build_dendritic_voltage_traces(db, suffix_dict=None, repartition=None):
    """Load dendritic voltage traces and add them to the database under the key ``dendritic_recordings``.

    Args:
        db (:py:class:`~data_base.DataBase`): The database to which the data should be added.
        suffix_dict (dict): Dictionary containing the suffixes of the dendritic voltage trace files.
            Default is ``None``, and they are inferred from the cell parameter files.
        repartition (bool): If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).

    Returns:
        None
    """
    assert repartition is not None
    logging.info("---building dendritic voltage traces dataframes---")

    try: 
        suffix = "vm_dend_traces.csv"
        filelist = make_filelist(db["simresult_path"], suffix=suffix)
    except ValueError: 
        suffix = "vm_dend_traces.npz"
        filelist = make_filelist(db["simresult_path"], sufix=suffix)

    recsite_labels = get_recsite_labels_from_dend_vt_filelist(filelist, full_suffix=suffix)

    logger.info("Loading dendritic voltage traces")

    if DEND_VT_SPLIT_PER_RECSITE_ID == True:
        dend_vt = load_dendritic_voltage_traces(db, filelist, recsite_labels, repartition=repartition)
        if not "dendritic_recordings" in list(db.keys()): db.create_sub_db("dendritic_recordings")
        sub_db = db["dendritic_recordings"]
        for recSiteLabel in list(suffix_dict.keys()):
            sub_db.set(recSiteLabel, dend_vt[recSiteLabel], dumper=DEFAULT_DUMPER)
    elif DEND_VT_SPLIT_PER_RECSITE_ID == False:
        if not len(filelist) == len(db["sim_trial_index"]):
            raise ValueError(
                "If DEND_VT_SPLIT_PER_RECSITE_ID is False, the amount of dendritic voltage traces should equal"
                "the sim_trial_index, but there are {} dendritic voltage traces and {} sim trial indices".format(
                    len(filelist), len(db["sim_trial_index"]))
                )
        dend_vt = load_dendritic_voltage_traces(db, filelist, recsite_labels, repartition=False)
        merged_df = dd.concat([*dend_vt.values()])
        db["dendritic_recordings"] = merged_df
        
    # db.set('dendritic_voltage_traces_keys', out.keys(), dumper = DEFAULT_DUMPER)


def _build_param_files(db, client):
    """Copy, transform and rename parameterfiles to a db.

    This function copies :ref:`cell_parameters_format`, :ref:`network_parameters_format`, :ref:`syn_file_format` files,
    and :ref:`con_file_format` files to the database.
    In the process, it renames each file to its hash and transforms the internal file references in the parameter files accordingly.

    Args:
        db (:py:class:`~data_base.DataBase`):
            The database to which the parameterfiles should be added.
        client (:py:class:`~dask.distributed.client.Client`): The Dask client to use for parallel computation.

    Returns:
        None. Sets the keys ``parameterfiles_cell_folder`` and ``parameterfiles_network_folder`` in the database.

    See also:
        The :ref:`cell_parameters_format` and :ref:`network_parameters_format` formats.

    Attention:
        This function assumes the database keys ``simresult_path`` and ``sim_trial_index`` already exist, which is likely
        only true when used in the context of the :py:meth:`~data_base.db_initializers.load_simrun_general.init` function.
    """
    logging.info("Moving parameter files")

    # Create target dir
    for target_d in [NEUP_DIR, NETP_DIR, SYN_DIR, CON_DIR, HOC_DIR, RECSITES_DIR]:
        if target_d in db.keys():
            del db[target_d]
        db.create_managed_folder(target_d)

    # Create table with paths to parameter files
    ds = construct_param_filename_hashmap_df(
        db["simresult_path"], db["sim_trial_index"]
    )
    futures = client.compute(ds)
    result = client.gather(futures)
    param_file_hash_df = pd.concat(result)
    param_file_hash_df.set_index("sim_trial_index", inplace=True)
    db.set("parameterfiles", param_file_hash_df, dumper=pandas_to_msgpack)

    # Copy and parameterfiles and adapt internal references
    parallel_resolve_and_copy_paramfiles_to_db(
        paramfile_hashmap_df=param_file_hash_df,
        db=db,
        client=client,
    )


def _get_recsite_labels_from_neup(neup):
    neuronParameters = scp.build_parameters(neup)
    rec_sites = neuronParameters.sim.recordingSites # absolute path to original .landmarkAscii file
    cell = scp.create_cell(neuronParameters.neuron, setUpBiophysics=True)
    recSiteManagers = [sca.RecordingSiteManager(recFile, cell) for recFile in rec_sites]
    return [recSite.label for RSManager in recSiteManagers for recSite in RSManager.recordingSites]


def _get_rec_site_label_fn_map(db, filelist):
    """Get the recording sites from the cell parameter files.

    Recording sites are locations onto the postsynaptic membrane where the voltage traces are recorded.
    This is used for recording the membrane voltage at non-somatic locations.

    Args:
        db (:py:class:`~data_base.DataBase`): The database to which the data should be added.

    Returns:
        dict: Dictionary containing the recording sites. It maps the label of the recording site to the suffix of the dendritic voltage trace files.

    Raises:
        NotImplementedError: If the cell parameter files of the simulation specify different recording sites for different trials.
    """
    rec_site_labels = get_recsite_labels_from_dend_vt_filelist(filelist)
    rec_sites = set(rec_sites)
    recsite_dend_vt_dict = {rslabel: rslabel + "_dend_vt_dict" for rslabel in rec_site_labels}
    return recsite_dend_vt_dict
