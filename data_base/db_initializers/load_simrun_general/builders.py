import glob
import logging
import os

import dask
import dask.dataframe as dd
import pandas as pd

import single_cell_parser as scp
import single_cell_parser.analyze as sca
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
from .file_handling import get_max_commas, make_filelist
from .metadata_utils import create_metadata, get_voltage_traces_divisions_by_metadata
from .param_file_parser import (
    _delayed_copy_transform_paramfiles_to_db,
    construct_param_filename_hashmap_df,
)
from .config import (
    NETP_DIR,
    NEUP_DIR,
    HOC_DIR,
    SYN_DIR,
    CON_DIR,
    RECSITES_DIR,
    DEFAULT_DUMPER
)

logger = logging.getLogger("ISF").getChild(__name__)


def _build_core(db, repartition=None, metadata_dumper=pandas_to_msgpack):
    """Parse the essential simulation results and add it to :paramref:`db`.

    The following data is parsed and added to the database:

    - filelist
    - somatic voltage traces
    - simulation trial index
    - metadata

    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): The database to which the data should be added.
        repartition (bool): If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
        metadata_dumper (function): Function to dump the metadata to disk. Default is :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.pandas_to_msgpack`.

    Returns:
        None
    """
    assert repartition is not None
    logging.info("---building data base core---")
    logging.info("generate filelist ...")

    # 1. Generate filelist containing paths to all soma voltage trace files
    try:
        filelist = make_filelist(db["simresult_path"], "vm_all_traces.csv")
    except ValueError:
        filelist = make_filelist(db["simresult_path"], "vm_all_traces.npz")
    db["filelist"] = filelist

    # 2. Generate dask dataframe containing the voltagetraces
    logging.info("generate voltage traces dataframe...")
    # vt = read_voltage_traces_by_filenames(db['simresult_path'], db['file_list'])
    vt = read_voltage_traces_by_filenames(
        db["simresult_path"], filelist, repartition=repartition
    )
    db.set("voltage_traces", vt, dumper=DEFAULT_DUMPER)

    # 3. Read out the sim_trial_index from the soma voltage traces dask dataframe
    logging.info("generate index ...")
    db["sim_trial_index"] = db["voltage_traces"].index.compute()

    # 4. Generate metadata dataframe out of sim_trial_indices
    logging.info("generate metadata ...")
    db.set("metadata", create_metadata(db), dumper=metadata_dumper)

    logging.info("add divisions to voltage traces dataframe")
    vt.divisions = get_voltage_traces_divisions_by_metadata(
        db["metadata"], repartition=repartition
    )
    db.set("voltage_traces", vt, dumper=DEFAULT_DUMPER)


def _build_synapse_activation(db, repartition=False, n_chunks=5000):
    """Parse the :ref:`syn_activation_format` and :ref:`spike_times_format` data.

    The synapse and presynaptic spike times data is added to the database under the keys
    ``synapse_activation`` and ``cell_activation`` respectively.

    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): The database to which the data should be added.
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
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): The database to which the data should be added.
        suffix_dict (dict): Dictionary containing the suffixes of the dendritic voltage trace files.
            Default is ``None``, and they are inferred from the cell parameter files.
        repartition (bool): If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).

    Returns:
        None
    """
    assert repartition is not None
    logging.info("---building dendritic voltage traces dataframes---")

    if suffix_dict is None:
        suffix_dict = _get_rec_site_managers(db)

    dend_vt = load_dendritic_voltage_traces(db, suffix_dict, repartition=repartition)
    if not "dendritic_recordings" in list(db.keys()):
        db.create_sub_db("dendritic_recordings")

    sub_db = db["dendritic_recordings"]

    for recSiteLabel in list(suffix_dict.keys()):
        sub_db.set(recSiteLabel, dend_vt[recSiteLabel], dumper=DEFAULT_DUMPER)
    # db.set('dendritic_voltage_traces_keys', out.keys(), dumper = DEFAULT_DUMPER)


def _build_param_files(db, client):
    """Copy, transform and rename parameterfiles to a db.

    This function copies :ref:`cell_parameters_format`, :ref:`network_parameters_format`, :ref:`syn_file_format` files,
    and :ref:`con_file_format` files to the database.
    In the process, it renames each file to its hash and transforms the internal file references in the parameter files accordingly.

    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
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

    # Copy and parameterfiles and adapt internal references
    ds = _delayed_copy_transform_paramfiles_to_db(
        paramfile_hashmap_df=param_file_hash_df,
        db=db,
        neup_path_column="path_neuron",
        neup_hash_column="hash_neuron",
        netp_path_column="path_network",
        netp_hash_column="hash_network",
    )
    futures = client.compute(ds)
    result = client.gather(futures)

    db.set("parameterfiles", param_file_hash_df, dumper=pandas_to_msgpack)


def _get_rec_site_managers(db):
    """Get the recording sites from the cell parameter files.

    Recording sites are locations onto the postsynaptic membrane where the voltage traces are recorded.
    This is used for recording the membrane voltage at non-somatic locations.

    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): The database to which the data should be added.

    Returns:
        dict: Dictionary containing the recording sites. It maps the label of the recording site to the suffix of the dendritic voltage trace files.

    Raises:
        NotImplementedError: If the cell parameter files of the simulation specify different recording sites for different trials.
    """
    param_files = glob.glob(os.path.join(db[NEUP_DIR], "*"))
    param_files = [
        p
        for p in param_files
        if not p.endswith(("Loader.pickle", "Loader.json", "metadata.json"))
    ]
    logging.info(len(param_files))
    rec_sites = []
    for param_file in param_files:
        neuronParameters = scp.build_parameters(param_file)
        rec_site = neuronParameters.sim.recordingSites
        rec_sites.append(tuple(rec_site))
    rec_sites = set(rec_sites)
    # print param_files
    if len(rec_sites) > 1:
        raise NotImplementedError(
            "Cannot initialize database with dendritic recordings if"
            + " the cell parameter files differ in the landmarks they specify for the recording sites."
        )
    #############
    # the following code is adapted from simrun
    #############
    neuronParameters = scp.build_parameters(param_files[0])
    neuronParameters = resolve_neup_reldb_paths(neuronParameters, db.basedir)
    rec_sites = neuronParameters.sim.recordingSites
    cellParam = neuronParameters.neuron
    with silence_stdout:
        cell = scp.create_cell(cellParam, setUpBiophysics=True)
    recSiteManagers = [sca.RecordingSiteManager(recFile, cell) for recFile in rec_sites]
    recsite_dend_vt_dict = {
        recSite.label: recSite.label + "_vm_dend_traces.csv"
        for RSManager in recSiteManagers
        for recSite in RSManager.recordingSites
    }
    return recsite_dend_vt_dict
