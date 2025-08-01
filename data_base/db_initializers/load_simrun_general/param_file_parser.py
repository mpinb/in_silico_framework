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
from .config import CON_DIR, HOC_DIR, NETP_DIR, NEUP_DIR, SYN_DIR, RECSITES_DIR
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
    logging.info("find unique parameterfiles")

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
    def _helper(df):
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
    delayeds = [_helper(df) for df in ddf]
    return delayeds


def _get_unique_syncons_from_netp(netp_fn):
    """Get the unique synapse and connection files from a list of network parameter files.

    Args:
        netp_fn (str): Path to the network parameter file.

    Returns:
        tuple: Tuple containing the unique synapse and connection files.
    """
    syn_files = []
    con_files = []
    netp = scp.build_parameters(netp_fn)
    for cell_type in list(netp["network"].keys()):
        if not "synapses" in netp["network"][cell_type]:
            continue  # key does not refer to a celltype
        con_files.append(netp["network"][cell_type]["synapses"]["connectionFile"])
        syn_files.append(netp["network"][cell_type]["synapses"]["distributionFile"])
    return syn_files, con_files


def _get_unique_hoc_fns_from_neup(neup_fn):
    """Get the unique hoc files from a list of neuron parameter files.

    Args:
        neup_fns (str): Path to the neuron parameter file.

    Returns:
        list: List containing the unique hoc files.
    """
    hoc_files = []
    neup = scp.build_parameters(neup_fn)
    hoc_files.append(neup["neuron"]["filename"])
    return hoc_files


def _get_unique_landmark_fns_from_neup(neup_fn):
    """Get the unique landmark files from a list of neuron parameter files.

    Args:
        neup_fns (str): Path to the neuron parameter file.

    Returns:
        list: List containing the unique landmark files.
    """
    landmark_files = []
    neup = scp.build_parameters(neup_fn)
    for landmark_file in neup["sim"]["recordingSites"]:
        landmark_files.append(landmark_file)
    return landmark_files


def _copy_and_transform_neuron_param(neup_fn, target_fn, hoc_fn_map, recsites_fn_map):
    """Convert all paths in a :ref:`cell_parameters_format` file to point to a hash filename.

    This function is used as a :paramref:`transform_fun` in
    :py:meth:`~data_base.db_initializers.load_simrun_general.write_param_files_to_folder`.

    Args:
        neuron (:py:class:`~single_cell_parser.parameters.NTParameterSet`): Dictionary containing the neuron model parameters.

    Attention:
        The new filepaths only exist once the relevant parameterfiles are also copied and renamed.
        This happens during the copying process in :py:meth:`~data_base.db_initializers.load_simrun_general.write_param_files_to_folder`.
    """
    neup = scp.build_parameters(neup_fn)
    neup = _convert_neup_fns_to_reldb(neup, hoc_fn_map, recsites_fn_map)
    neup.save(target_fn)
    return True


def _copy_and_transform_network_param(netp_fn, target_fn, syn_fn_map, con_fn_map):
    """Convert all paths in a :ref:`network_parameters_format` file.

    This function is used as a :paramref:`transform_fun` in
    :py:meth:`~data_base.db_initializers.load_simrun_general.write_param_files_to_folder`.

    Args:
        network (:py:class:`~single_cell_parser.parameters.NTParameterSet`): Dictionary containing the network model parameters.

    Attention:
        The new filepaths only exist once the relevant parameterfiles are also copied and renamed.
        This happens during the copying process in :py:meth:`~data_base.db_initializers.load_simrun_general.write_param_files_to_folder`.
    """
    netp = scp.build_parameters(netp_fn)
    netp = _convert_netp_fns_to_reldb(netp, syn_fn_map, con_fn_map)
    netp.save(target_fn)
    return True


def _copy_and_transform_syn(syn_fn, target_fn, hoc_fn_map):
    """Copy, rename and transform a single :ref:`syn_file_format` file.

    The :ref:`syn_file_format` file is copied to the target directory, renamed to its hash, and the hoc file name is replaced.

    Args:
        syn_fn (str): Path to the synapse distribution file.
        new_hoc (str): Path to the new hoc file.
    """
    with open(syn_fn, "r") as f:
        content = f.read()

    content = _convert_syn_fns_to_reldb(content, hoc_fn_map)
    with open(target_fn, "w") as f:
        f.write("".join(content))
    return syn_fn


def _copy_and_transform_con(con_fn, target_fn, syn_fn_map):
    """Copy, rename and transform a single :ref:`con_file_format` file.

    The :ref:`con_file_format` file is copied to the target directory, renamed to its hash, and the synapse distribution file name is replaced.

    Args:
        con_fn (str): Path to the connection file.
        new_syn (str): Path to the new synapse distribution file.
    """
    with open(con_fn, "r") as f:
        content = f.read()

    content = _convert_con_fns_to_reldb(content, syn_fn_map, con_fn)
    with open(target_fn, "w") as f:
        f.write("".join(content))
    return con_fn


def _generate_target_filename(db, dir_name, fn, hash_rename=True):
    """Generate a target filename for a file to be copied to the database.

    Args:
        db (:py:class:`~data_base.DataBase`): The database to which the data should be added.
        dir_name (str): The directory name in the database where the file should be copied.
        fn (str): The original file name.
        hash_rename (bool): Whether to rename the file to its hash. Defaults to True.
    Returns:
        str: The target filename in the database.
    """
    if hash_rename:
        new_fn = _hash_file_content(fn)
    else:
        new_fn = os.path.basename(fn)
    return os.path.join(db.basedir, dir_name, new_fn)


def _extract_unique_files(
    paramfile_hashmap_df,
    neup_path_column="path_neuron",
    neup_hash_column="hash_neuron", 
    netp_path_column="path_network",
    netp_hash_column="hash_network",
    client=None,
):
    """
    Phase 1: Extract all unique files from parameter files.
    
    Returns:
        dict: Contains all unique file lists
    """
    
    # Get unique parameter files
    cell_param_fns = paramfile_hashmap_df.drop_duplicates(subset=neup_hash_column)[neup_path_column].tolist()
    netp_param_fns = paramfile_hashmap_df.drop_duplicates(subset=netp_hash_column)[netp_path_column].tolist()
    
    logger.info(f"{len(netp_param_fns)} unique network parameter files")
    logger.info(f"{len(cell_param_fns)} unique neuron parameter files")
    
    # Extract unique files in parallel
    logger.info("Extracting unique synapse, connection, hoc, and landmark files")
    
    # Submit all extraction jobs
    syn_con_futures = [client.submit(_get_unique_syncons_from_netp, fn) for fn in netp_param_fns]
    hoc_futures = [client.submit(_get_unique_hoc_fns_from_neup, fn) for fn in cell_param_fns]
    landmark_futures = [client.submit(_get_unique_landmark_fns_from_neup, fn) for fn in cell_param_fns]
    
    # Collect and deduplicate results
    from dask.distributed import as_completed
    
    syn_fns_set = set()
    con_fns_set = set()
    
    for future in as_completed(syn_con_futures):
        syn_list, con_list = future.result()
        syn_fns_set.update(syn_list)
        con_fns_set.update(con_list)
    
    hoc_fns_set = set()
    for future in as_completed(hoc_futures):
        hoc_fns_set.update(future.result())
    
    landmark_fns_set = set()
    for future in as_completed(landmark_futures):
        landmark_fns_set.update(future.result())
    
    # Convert to sorted lists for reproducible results
    file_lists = {
        'syn_fns': sorted(list(syn_fns_set)),
        'con_fns': sorted(list(con_fns_set)), 
        'hoc_fns': sorted(list(hoc_fns_set)),
        'landmark_fns': sorted(list(landmark_fns_set)),
        'cell_param_fns': cell_param_fns,
        'netp_param_fns': netp_param_fns,
    }
    
    logger.info(f"{len(file_lists['hoc_fns'])} unique .hoc files")
    logger.info(f"{len(file_lists['landmark_fns'])} unique .landmark files") 
    logger.info(f"{len(file_lists['syn_fns'])} unique .syn files")
    logger.info(f"{len(file_lists['con_fns'])} unique .con files")
    
    return file_lists


def _create_source_target_maps(file_lists, db, client=None):
    """
    Phase 2: Generate target filenames and create source->target mappings.
    
    Args:
        file_lists (dict): Dictionary of file lists from _extract_unique_files
        db: Database object
        client: Dask client
        
    Returns:
        dict: Contains target filenames and mapping dictionaries
    """
    
    logger.info("Generating target filenames")
    
    # Configuration for each file type
    file_configs = [
        ('hoc_fns', HOC_DIR, False),
        ('landmark_fns', RECSITES_DIR, False),
        ('syn_fns', SYN_DIR, True),
        ('con_fns', CON_DIR, True),
        ('cell_param_fns', NEUP_DIR, True),
        ('netp_param_fns', NETP_DIR, True),
    ]
    
    target_filenames = {}
    filename_maps = {}
    
    for file_key, directory, hash_rename in file_configs:
        file_list = file_lists[file_key]
        
        if not file_list:  # Skip empty lists
            target_filenames[file_key] = []
            continue
        
        # Generate target filenames in parallel
        target_futures = [
            client.submit(_generate_target_filename, db, directory, fn, hash_rename)
            for fn in file_list
        ]
        target_list = [f.result() for f in target_futures]
        
        target_filenames[file_key] = target_list
        
        # Create source->target mapping for files that need transformation
        if file_key in ['hoc_fns', 'landmark_fns', 'syn_fns', 'con_fns']:
            map_name = file_key.replace('_fns', '_fn_map')
            filename_maps[map_name] = dict(zip(file_list, target_list))
    
    # Rename landmark map to match expected name in transformation functions
    if 'landmark_fn_map' in filename_maps:
        filename_maps['recsites_fn_map'] = filename_maps.pop('landmark_fn_map')
    
    return {
        'target_filenames': target_filenames, 
        'filename_maps': filename_maps,
    }


def _create_delayed_copy_operations(file_lists, target_filenames, filename_maps):
    """
    Phase 3: Create delayed copy and transform operations.
    
    Args:
        file_lists (dict): Dictionary of source file lists
        target_filenames (dict): Dictionary of target filename lists
        filename_maps (dict): Dictionary of source->target mappings
        
    Returns:
        list: List of dask.delayed objects for copying/transforming files
    """
    
    logger.info("Creating delayed copy operations")
    
    operations = []
    
    # Simple file copies (no transformation needed)
    simple_copy_configs = [
        ('hoc_fns', 'hoc_fns'),
        ('landmark_fns', 'landmark_fns'),
    ]
    
    for source_key, target_key in simple_copy_configs:
        source_files = file_lists[source_key]
        target_files = target_filenames[target_key]
        
        operations.extend([
            dask.delayed(shutil.copy)(source_fn, target_fn)
            for source_fn, target_fn in zip(source_files, target_files)
        ])
    
    # Files that need transformation
    transform_configs = [
        ('syn_fns', 'syn_fns', _copy_and_transform_syn, ['hoc_fn_map']),
        ('con_fns', 'con_fns', _copy_and_transform_con, ['syn_fn_map']),
        ('cell_param_fns', 'cell_param_fns', _copy_and_transform_neuron_param, ['hoc_fn_map', 'recsites_fn_map']),
        ('netp_param_fns', 'netp_param_fns', _copy_and_transform_network_param, ['syn_fn_map', 'con_fn_map']),
    ]
    
    for source_key, target_key, transform_func, required_maps in transform_configs:
        source_files = file_lists[source_key]
        target_files = target_filenames[target_key]
        
        # Get the required mapping dictionaries
        maps = [filename_maps[map_name] for map_name in required_maps]
        
        operations.extend([
            dask.delayed(transform_func)(source_fn, target_fn, *maps)
            for source_fn, target_fn in zip(source_files, target_files)
        ])
    
    logger.info(f"Created {len(operations)} delayed copy operations")
    return operations


def _delayed_copy_transform_paramfiles_to_db(
    paramfile_hashmap_df,
    db,
    neup_path_column="path_neuron",
    neup_hash_column="hash_neuron",
    netp_path_column="path_network", 
    netp_hash_column="hash_network",
    client=None,
):
    """
    Orchestrate the three-phase process for copying and transforming parameter files.
    
    Phase 1: Extract unique files
    Phase 2: Create source->target mappings  
    Phase 3: Create delayed copy operations
    """
    
    # Phase 1: Extract all unique files
    file_lists = _extract_unique_files(
        paramfile_hashmap_df=paramfile_hashmap_df,
        neup_path_column=neup_path_column,
        neup_hash_column=neup_hash_column,
        netp_path_column=netp_path_column,
        netp_hash_column=netp_hash_column,
        client=client,
    )
    
    # Phase 2: Generate target filenames and create mappings
    mapping_data = _create_source_target_maps(
        file_lists=file_lists,
        db=db,
        client=client,
    )
    
    # Phase 3: Create delayed operations
    delayed_operations = _create_delayed_copy_operations(
        file_lists=file_lists,
        target_filenames=mapping_data['target_filenames'],
        filename_maps=mapping_data['filename_maps'],
    )
    
    return delayed_operations


def load_param_files_from_db(db, sti):
    """Load the :ref:`cell_parameters_format` and :ref:`network_parameters_format` files from the database.

    Args:
        db (:py:class:`~data_base.DataBase`):
            The database containing the parsed simulation results.
        sti (str):
            For which simulation trial index to load the parameter files.

    Returns:
        tuple: The :py:class:`~single_cell_parser.parameters.NTParameterSet` objects for the cell and network.
    """
    import single_cell_parser as scp

    x = db["parameterfiles"].loc[sti]
    x_neu, x_net = x["hash_neuron"], x["hash_network"]
    neuf = db[NEUP_DIR].join(x_neu)
    netf = db[NETP_DIR].join(x_net)
    return scp.build_parameters(neuf), scp.build_parameters(netf)
