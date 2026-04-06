import logging
import os
import shutil

import dask
import dask.dataframe as dd
import pandas as pd

import single_cell_parser as scp

from .filepath_resolution import (
    _convert_netp_fns_to_reldb, 
    _convert_neup_fns_to_reldb, 
    _convert_syn_fns_to_reldb, 
    _convert_con_fns_to_reldb
)
from .file_handling import get_file
from .utils import _hash_file_content

logger = logging.getLogger("ISF").getChild(__name__)


def construct_param_filename_hashmap_df(simresult_path, sim_trial_index):
    """Generate a hashmap for the paths of :ref:`cell_parameters_format` and :ref:`network_parameters_format` files.

    For each trial, this function fetches the paths of the :ref:`cell_parameters_format` and :ref:`network_parameters_format` files,
    and creates a hash of their content. This hashmap is used to copy over the parameter files to the database.

    For any same network embedding, the :ref:`network_parameters_format` file is the same, and for any same biophysically detailed neuron model,
    the :ref:`cell_parameters_format` file is the same. Many of the simulation trials will therefore share the same parameter files.
    This is a convenience function to generate a DataFrame containing the paths and hashes of the original simrun parameter files for a collection of simulation trials.
    As not all trials necessarilly share the same network embedding or neuron model, the DataFrame will likely (but not necessarily) contain different entries across trials.

    Args:
        simresult_path (str): Path to the simulation results folder.
        sim_trial_index (array): array of sim_trial_indices to generate paramfiles for.

    Returns:
        list: list of dask.delayed objects to calculate the pd.DataFrame objects containing the paths to the parameter files and their hashes.

    Example::

        >>> simresult_path = 'results/date_seed_pid'
        >>> os.listdir(simresult_path)
        [
            'simulation_run000000_synapses.csv', 'simulation_run000000_presynaptic_cells.csv'
            'simulation_run000001_synapses.csv', 'simulation_run000001_presynaptic_cells.csv'
            ...
            pid_neuron_model.param, pid_network_model.param
        ]
        >>> delayeds = generate_param_file_hashes(simresult_path, ['path/pid/000000', 'path/pid/000001'])
        >>> futures = dask.compute(delayeds)
        >>> result = client.gather(futures)
        >>> parameterfiles = pd.concat(result)
        >>> parameterfiles
                                path_neuron             path_network hash_neuron    hash_network
        sim_trial_index
        0 path/pid/000000       pid_neuron_model.param pid_network_model.param     0b1
        1 path/pid/000001       pid_neuron_model.param pid_network_model.param     0b2
        ...


    """
    logging.info("Mapping sim_trial_index to parameter files...")

    def get_simrun_dir_and_pid(row):
        sim_result_dir = os.path.dirname(row.sim_trial_index)
        pid = os.path.basename(sim_result_dir).split("_")[-1]
        return sim_result_dir, pid

    def get_original_netp_fn_from_trial(row):
        sim_result_dir, pid = get_simrun_dir_and_pid(row)
        # return os.path.join(simresult_path, sim_trial_folder, identifier + '_network_model.param')
        return get_file(
            os.path.join(simresult_path, sim_result_dir), "_network_model.param"
        )

    def get_original_neup_fn_from_trial(row):
        sim_result_dir, pid = get_simrun_dir_and_pid(row)
        # return os.path.join(simresult_path, sim_trial_folder, identifier + '_neuron_model.param')
        return get_file(
            os.path.join(simresult_path, sim_result_dir), "_neuron_model.param"
        )

    @dask.delayed
    def _delayed_construct_paramfile_df(df):
        ## todo: crashes if specified folder directly contains the param files
        ## and not a subfolder containing the param files
        df["path_neuron"] = df.apply(
            lambda x: get_original_neup_fn_from_trial(x), axis=1
        )
        df["path_network"] = df.apply(
            lambda x: get_original_netp_fn_from_trial(x), axis=1
        )
        df["hash_neuron"] = df["path_neuron"].map(_hash_file_content)
        df["hash_network"] = df["path_network"].map(_hash_file_content)
        return df

    df = pd.DataFrame(dict(sim_trial_index=list(sim_trial_index)))
    ddf = dd.from_pandas(df, npartitions=3000).to_delayed()
    delayeds = [_delayed_construct_paramfile_df(df) for df in ddf]
    return delayeds


def _get_syn_con_fns_from_netp(netp_fn):
    """Get the unique synapse and connection files from a list of network parameter files.

    Args:
        netp_fn (str): Path to the :ref:`network_parameters_format` file.

    Returns:
        tuple: Tuple containing the unique synapse and connection files.
    """
    syn_files, con_files = scp.parameters.fast_extract_values_from_param_file_key(netp_fn, ["distributionFile", "connectionFile"])
    # syn_files = []
    # con_files = []
    # netp = scp.build_parameters(netp_fn)
    # for cell_type in list(netp["network"].keys()):
    #     if not "synapses" in netp["network"][cell_type]:
    #         continue  # key does not refer to a celltype
    #     con_files.append(netp["network"][cell_type]["synapses"]["connectionFile"])
    #     syn_files.append(netp["network"][cell_type]["synapses"]["distributionFile"])
    return syn_files, con_files


def _get_morph_fns_from_neup(neup_fn):
    """Get the unique morphology files from a list of neuron parameter files.

    Args:
        neup_fn (str): Path to the neuron parameter file.

    Returns:
        list: List containing the unique morphpology files.
    """
    morph_files, = scp.parameters.fast_extract_values_from_param_file_key(neup_fn, ["filename"])
    return morph_files


def _get_recsite_fns_from_neup(neup_fn):
    """Get the unique recsite files from a list of neuron parameter files.

    Args:
        neup_fn (str): Path to the neuron parameter file.

    Returns:
        list: List containing the unique recsite files.
    """
    # Don't use fast_extract_values_from_param_file_key here, since recordingsites are usually arrays.
    recsite_files = []
    neup = scp.build_parameters(neup_fn)
    for recsite_file in neup["sim"]["recordingSites"]:
        recsite_files.append(recsite_file)
    return recsite_files


def _resolve_and_copy_neuron_param(neup_fn, scattered_fn_map):
    """Convert all references to  :ref:`morphology_file_format` and recsite .landmarkAscii files 
    in a :ref:`network_parameters_format` file and copy to a new location.

    Args:
        neup_fn (str): Path to a :ref:`cell_parameters_format` file.
        scattered_fn_map (:class:`distributed.Future`): 
            A future dictionary with filename mappings. Must contain the keys "syn", "con" and "netp"

    Attention:
        The resolved paths do not necessarily exist yet.
    """
    morph_fn_map = scattered_fn_map['morph']
    recsites_fn_map = scattered_fn_map['recsites']
    target_fn = scattered_fn_map['neup'][neup_fn] 
    
    neup = scp.build_parameters(neup_fn)
    neup = _convert_neup_fns_to_reldb(neup, morph_fn_map, recsites_fn_map)
    try:
        neup.save(target_fn)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(target_fn), exist_ok=True)
        neup.save(target_fn)


def _resolve_and_copy_network_param(netp_fn, scattered_fn_map):
    """Convert all references to  :ref:`syn_file_format` and :ref:`con_file_format` files 
    in a :ref:`network_parameters_format` file and copy to a new location.

    Args:
        netp_fn (str): Path to a :ref:`network_parameters_format` file.
        scattered_fn_map (:class:`distributed.Future`): 
            A future dictionary with filename mappings. Must contain the keys "syn", "con" and "netp"

    Attention:
        The resolved paths do not necessarily exist yet.
    """
    syn_fn_map = scattered_fn_map['syn']
    con_fn_map = scattered_fn_map['con']
    target_fn = scattered_fn_map['netp'][netp_fn]
    
    # TODO: this can be faster by using regex replace instead of 
    # building the entire .param file, similar to fast_extract_values_from_param_file
    # but eh, its robust this way and acceptably fast for now (takes like 3mins for 10k files on 40 workers)
    netp = scp.build_parameters(netp_fn)  
    netp = _convert_netp_fns_to_reldb(netp, syn_fn_map, con_fn_map)
    try:
        netp.save(target_fn)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(target_fn), exist_ok=True)
        netp.save(target_fn)


def _resolve_and_copy_syn(syn_fn, scattered_fn_map):
    """Resolve the reference to a :ref:`morphology_file_format` file and 
    copy a single :ref:`syn_file_format` file to a new location.

    Args:
        syn_fn (str): Path to the synapse distribution file.
        scattered_fn_map (:class:`distributed.Future`): 
            A future dictionary with filename mappings. Must contain the keys "syn" and "morph".

    Returns:
        str: The new :ref:`syn_file_format` filename.
    """
    morph_fn_map = scattered_fn_map['morph']
    target_fn = scattered_fn_map['syn'][syn_fn]
    
    with open(syn_fn, "r") as f:
        content = f.read()

    logger.debug("Converting morphology filenames in {}".format(syn_fn))
    content = _convert_syn_fns_to_reldb(content, morph_fn_map)
    try:
        with open(target_fn, "w") as f:
            f.write("".join(content))
    except FileNotFoundError:
        os.makedirs(os.path.dirname(target_fn), exist_ok=True)
        with open(target_fn, "w") as f:
            f.write("".join(content))
    return syn_fn


def _resolve_and_copy_con(con_fn, scattered_fn_map):
    """Resolve the reference to a :ref:`syn_file_format` file and 
    copy a single :ref:`con_file_format` file to a new location.

    Args:
        con_fn (str): Path to the synapse distribution file.
        scattered_fn_map (:class:`distributed.Future`): 
            A future dictionary with filename mappings. Must contain the keys "syn" and "con".

    Returns:
        str: The new :ref:`con_file_format` filename.
    """
    syn_fn_map = scattered_fn_map['syn']
    target_fn = scattered_fn_map['con'][con_fn]
    
    with open(con_fn, "r") as f:
        content = f.read()

    content = _convert_con_fns_to_reldb(content, syn_fn_map, con_fn)
    try:
        with open(target_fn, "w") as f:
            f.write("".join(content))
    except FileNotFoundError:
        os.makedirs(os.path.dirname(target_fn), exist_ok=True)
        with open(target_fn, "w") as f:
            f.write("".join(content))
    return con_fn


def _generate_target_filenames(db, db_target_dir, filelist, copy_method="remount", client=None):
    """Generate target filenames within a database directory for an array of source files.
    
    The target filenames can be configured in :mod:`~data_base.db_initializers.load_simrun_general.config`
    by changing :attr:`PARAM_FILE_COPY_METHOD` and the target directory names of each file type.

    Args:
        db (:class:`~data_base.DataBase`): The database to which the data should be added.
        db_target_dir (str): 
            The directory relative to the database where the files of one type should be copied.
            These directories will be a :class:`data_base.isf_data_base.ManagedFolder`
        filelist (List[str]): The original file names.
        copy_method (str): ``"remount"`` to preserve relative directory structure or ``"hash_rename"`` to rename to a hash and copy to the same location.
        client (:class:`distributed.client.Client`):
            A parallellization client. Only needed if ``"PARAMFILE_COPY_METHOD"`` is configured to ``"hash_rename"``

    Returns:
        str: The target filename in the database.
    """
    if copy_method == "hash_rename":
        assert client is not None, "Please pass a parallellization client for hash renaming the files"
        # New param file name will be the content hash
        new_base_fns = client.gather(client.map(_hash_file_content, filelist))
    elif copy_method == "remount":
        assert len(filelist) > 1, "Can't calculate the relative directory structure from a single file, so copy_method='remount' can't be used here. Consider using copy_method='hash_rename' instead. Filelist: {}".format(filelist)
        # paramfiles are copied over in the same folder structure.
        base_fn = os.path.commonpath(filelist)
        # Not worth parallellizing for now, it's fast enough. Overhead of sending to client may be slower than this
        new_base_fns = [os.path.relpath(e, start=base_fn) for e in filelist]
    else:
        raise ValueError("Config value PARAM_FILE_COPY_METHOD={} is not supported. SUpported values are hash_rename or remount.")
    new_fns = [
        os.path.join(db.basedir, db_target_dir, e) 
        for e in new_base_fns
        ]
    return new_fns


def _extract_unique_references_from_neup_and_netp(
    paramfile_hashmap_df,
    client=None,
    filter_param_files_by_content=False,
):
    """
    Extract all unique references to :ref:`syn_file_format` and :ref:`con_file_format` files from :ref:`network_parameters_format`,
    and all unique references to :ref:`morphology_file_format` and recsite files from :ref:`cell_parameters_format`.
    
    Args:
        paramfile_hashmap_df (:class:`pandas.DataFrame`):
            A pandas dataframe containing all :ref:`cell_parameters_format` and :ref:`network_parameters_format`,
            as well as a hash of their content.
            Should normally be created by :py:meth:`construct_param_filename_hashmap_df`
        filter_param_files_by_content (bool): Whether to filter out parameter files with identical content
        client (:py:class:`distributed.client.Client`):
            A parallellization client. 
   
    Returns:
        Dict[str, List]: A dictionary mapping each filetype (str) to a list of unique references of that filetype. 
    """
    neup_path_column="path_neuron"
    neup_hash_column="hash_neuron" 
    netp_path_column="path_network"
    netp_hash_column="hash_network"

    # Get unique parameter files, unique meaning unique content
    if filter_param_files_by_content == True:
        cell_param_fns = paramfile_hashmap_df.drop_duplicates(subset=neup_hash_column)[neup_path_column].tolist()
        netp_param_fns = paramfile_hashmap_df.drop_duplicates(subset=netp_hash_column)[netp_path_column].tolist()
    # Get unique parameter files, unique meaning unique filepath
    else:
        cell_param_fns = paramfile_hashmap_df[neup_path_column].tolist()
        netp_param_fns = paramfile_hashmap_df[netp_path_column].tolist()
    
    logger.info(f"{len(netp_param_fns)} unique network parameter files")
    logger.info(f"{len(cell_param_fns)} unique neuron parameter files")
    
    # Extract unique files in parallel
    logger.info("Extracting unique .syn, .con, morphology, and recsite references from neuron and network parameters")
    
    # Submit all extraction jobs
    syn_con_futures = client.map(_get_syn_con_fns_from_netp, netp_param_fns)
    morph_futures = client.map(_get_morph_fns_from_neup,  cell_param_fns)
    recsites_futures = client.map(_get_recsite_fns_from_neup,  cell_param_fns)
    
    # Collect and deduplicate results
    syn_fns_unique = []
    con_fns_unique = []
    for worker_result in client.gather(syn_con_futures):
        syn_fns_unique.extend(worker_result[0])
        con_fns_unique.extend(worker_result[1])
    syn_fns_unique = list(set(syn_fns_unique))
    con_fns_unique = list(set(con_fns_unique))

    morph_fns_unique = []
    for worker_result in client.gather(morph_futures):
        morph_fns_unique.extend(worker_result)
    morph_fns_unique = list(set(morph_fns_unique))

    
    recsites_fns_unique = []
    for worker_result in client.gather(recsites_futures):
        recsites_fns_unique.extend(worker_result)
    recsites_fns_unique = list(set(recsites_fns_unique))
    
    # Convert to sorted lists for reproducible results
    file_lists = {
        'syn': syn_fns_unique,
        'con': con_fns_unique, 
        'morph': morph_fns_unique,
        'recsites': recsites_fns_unique,
        'neup': cell_param_fns,
        'netp': netp_param_fns,
    }
    
    logger.info(f"{len(file_lists['morph'])} unique .morph files")
    logger.info(f"{len(file_lists['recsites'])} unique recsite files") 
    logger.info(f"{len(file_lists['syn'])} unique .syn files")
    logger.info(f"{len(file_lists['con'])} unique .con files")
    
    return file_lists


def _safe_copy(source, target):
    """Copy a file from :param:`source` to :param:`target`.
    
    Creates the parent directories if they do not exist yet.

    Args:
        source (str): Original filename
        target (str): Desired target location to copy :param:`source` to.
    """
    try:
        shutil.copy(source, target)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy(source, target)


def _create_filename_maps(source_files_dict, db, paramfile_target_dirs, copy_method="remount", client=None):
    """Create filename ``source -> target`` maps for all file types.
    
    Each key in the resulting map refers to a filetype present in :param:`filetype_target_dir_map`.
    The filetype keys have `source -> target` mappings for all files of that filetype.

    Args:
        source_files_dict (Dict[str, List[str]]):
            A dictionary mapping file types (str) to their source filepaths.
        db (:class:`~data_base.isf_data_base.DataBase`):
            The target database where files should be copied to. 
        copy_method (str): Which copy strategy to use. 
            Must be either ``"hash_rename"`` or ``"remount"``. 
            ``"hash_rename"`` will rename all parameterfiles to a hash of their content. 
            ``"remount"`` will preserve the relative directory structure of the parameterfiles.
        paramfile_target_dirs (dict): 
            Dictionary containing configuration on how to organise parameterfiles in the database. Options are:

            - "neup" (str): Target directory name of :ref:`cell_parameters_format`. Default is ``"parameterfiles_folder"``
            - "netp" (str): Target directory name of :ref:`network_parameters_format`. Default is ``"parameterfiles_folder"``
            - "morph" (str): Target directory name of :ref:`morphology_file_format` files. Default is ``"anatomy_folder"``
            - "syn" (str): Target directory name of :ref:`syn_file_format` files. Default is ``"anatomy_folder"``
            - "con" (str): Target directory name of :ref:`con_file_format` files. Default is ``"anatomy_folder"``
            - "recsites" (str): Target directory name of recordingsites (``.landmarkAscii``). Default is "anatomy_folder"
            
    Returns:
        Dict[str, Dict[str, str]]:
            A dictionary mapping file types (str) to their ``source -> target`` filename maps.
    """
    assert client is not None
    target_files = {}
    for file_type, dir_path in paramfile_target_dirs.items():
        target_files[file_type] = _generate_target_filenames(
            db=db,
            db_target_dir=dir_path,
            filelist=source_files_dict[file_type],
            copy_method=copy_method,
            client=client
        )
    
    # Create maps on cluster
    fn_maps = {}
    for file_type in paramfile_target_dirs.keys():
        fn_maps[file_type] = dict(zip(source_files_dict[file_type], target_files[file_type]))
    
    return fn_maps


def parallel_resolve_and_copy_paramfiles_to_db(
    paramfile_hashmap_df,
    db,
    paramfile_target_dirs=None,
    copy_method="remount",
    client=None,
):
    """Resolve and copy all relevant parameter files to a database.
    
    This function:
    
    1. Fetches all :ref:`network_parameters_format` and :ref:`cell_parameters_format`
    2. Fetches all unique references to :ref:`syn_file_format`, :ref:`con_file_format`, :ref:`morphology_file_format` and recsite (.landmarkAscii) files from these parameter files
    3. Creates a mapping for each file from original location to target location, depending on the config.
    4. Scatters this filename mapping dict to a distsributed cluster
    5. Resolves all references to :ref:`syn_file_format`, :ref:`con_file_format`, :ref:`morphology_file_format` and recsite (.landmarkAscii) files in each file depending on this map.
    6. Copies over all resolved files from source to target.
    
    The resolution and copying is done in a single pass for efficiency.

    Args:
        paramfile_hashmap_df (pd.DataFrame): 
            A dataframe containing all :ref:`network_parameters_format` and :ref:`cell_parameters_format` files, as well as their hash.
            This is used in :func:`_extract_unique_references_from_neup_and_netp`
        db (:class:`data_base.data_base.DataBase`): The database that is being initialized
        client (distributed.Client): A distributed client for parallel computation.
        copy_method (str): Which copy strategy to use. Must be either ``"hash_rename"`` or ``"remount"``. 
            ``"hash_rename"`` will rename all parameterfiles to a hash of their content. 
            ``"remount"`` will preserve the relative directory structure of the parameterfiles.
        paramfile_target_dirs (dict, optional): 
            Dictionary mapping parameter file types to their desired target directory in the database. Keys include:

            - "neup" (str): Target directory name of :ref:`cell_parameters_format`. Default is ``"parameterfiles_folder"``
            - "netp" (str): Target directory name of :ref:`network_parameters_format`. Default is ``"parameterfiles_folder"``
            - "morph" (str): Target directory name of :ref:`morphology_file_format` files. Default is ``"anatomy_folder"``
            - "syn" (str): Target directory name of :ref:`syn_file_format` files. Default is ``"anatomy_folder"``
            - "con" (str): Target directory name of :ref:`con_file_format` files. Default is ``"anatomy_folder"``
            - "recsites" (str): Target directory name of recordingsites (``.landmarkAscii``). Default is "anatomy_folder"
    
    Returns:
        dict: The filename map for each file type.
    """
    
    # Phase 1: Extract all unique files from parameter files
    source_file_list = _extract_unique_references_from_neup_and_netp(
        paramfile_hashmap_df=paramfile_hashmap_df,
        client=client,
        filter_param_files_by_content=True if copy_method == "hash_rename" else False
    )

    # Create filename map and scatter to cluster
    fn_maps = _create_filename_maps(
        source_files_dict=source_file_list,
        db=db,
        paramfile_target_dirs=paramfile_target_dirs,
        copy_method=copy_method,
        client=client
    )
    scattered_maps = client.scatter(fn_maps, broadcast=True)
    
    # copy and transform param files to target location
    fut_morph = client.map(_safe_copy, *zip(*fn_maps['morph'].items()))
    fut_recsites = client.map(_safe_copy, *zip(*fn_maps['recsites'].items()))
    fut_con = client.map(
        _resolve_and_copy_con,
        source_file_list['con'],
        [scattered_maps]*len(source_file_list['con'])
    )
    fut_syn = client.map(
        _resolve_and_copy_syn,
        source_file_list['syn'],
        [scattered_maps]*len(source_file_list['syn'])
    )
    fut_neup = client.map(
        _resolve_and_copy_neuron_param,
        source_file_list['neup'],
        [scattered_maps]*len(source_file_list['neup'])
    )
    fut_netp = client.map(
        _resolve_and_copy_network_param,
        source_file_list['netp'],
        [scattered_maps]*len(source_file_list['netp'])
    )

    client.gather(fut_morph)
    logger.info("Morphology files copied to {}".format(paramfile_target_dirs['morph']))
    client.gather(fut_recsites)
    logger.info("Recordings site files (.landmarkAscii) copied to {}".format(paramfile_target_dirs['recsites']))
    client.gather(fut_con)
    logger.info("Synapse connectivity files (.con) resolved and copied to {}".format(paramfile_target_dirs['con']))
    client.gather(fut_syn)
    logger.info("Synapse distribution files (.syn) resolved and copied to {}".format(paramfile_target_dirs['syn']))
    client.gather(fut_neup)
    logger.info("Neuron parameter files (.param) resolved and copied to {}".format(paramfile_target_dirs['neup']))
    client.gather(fut_netp)
    logger.info("Network parameter files (.param) resolved and copied to {}".format(paramfile_target_dirs['netp']))

    return fn_maps
    

def load_param_files_from_db(db, sti):
    """Load the :ref:`cell_parameters_format` and :ref:`network_parameters_format` files from the database.

    Args:
        db (:class:`~data_base.DataBase`):
            The database containing the parsed simulation results.
        sti (str):
            For which simulation trial index to load the parameter files.

    Returns:
        tuple: The :class:`~single_cell_parser.parameters.NTParameterSet` objects for the cell and network.
    """
    import single_cell_parser as scp

    x = db["parameterfiles"].loc[sti]
    neup_fn, netp_fn = x["path_neuron"], x["path_network"]
    return scp.build_parameters(neup_fn), scp.build_parameters(netp_fn)
