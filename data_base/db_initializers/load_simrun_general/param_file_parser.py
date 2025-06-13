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

    def get_original_neup_fn_from_trial(x):
        sim_result_dir, pid = get_simrun_dir_and_pid(x)
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


def _copy_and_transform_neuron_param(neup_fn, target_fn, hoc_fn_map, recsites_fn_map):
    """Convert all paths in a :ref:`cell_parameters_format` file to point to a hash filename.

    This function is used as a :paramref:`transform_fun` in
    :py:meth:`~data_base.db_initializers.load_simrun_general.write_param_files_to_folder`.

    Args:
        neuron (:py:class:`~single_cell_parser.parameters.ParameterSet`): Dictionary containing the neuron model parameters.

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
        network (:py:class:`~single_cell_parser.parameters.ParameterSet`): Dictionary containing the network model parameters.

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


def _get_unique_syncons_from_netps(netp_fns):
    """Get the unique synapse and connection files from a list of network parameter files.

    Args:
        netp_fn (str): Path to the network parameter file.

    Returns:
        tuple: Tuple containing the unique synapse and connection files.
    """
    syn_files = []
    con_files = []
    for netp_fn in netp_fns:
        netp = scp.build_parameters(netp_fn)
        for cell_type in list(netp["network"].keys()):
            if not "synapses" in netp["network"][cell_type]:
                continue  # key does not refer to a celltype
            con_files.append(netp["network"][cell_type]["synapses"]["connectionFile"])
            syn_files.append(netp["network"][cell_type]["synapses"]["distributionFile"])
    return list(set(syn_files)), list(set(con_files))


def _get_unique_hoc_fns_from_neups(neup_fns):
    """Get the unique hoc files from a list of neuron parameter files.

    Args:
        neup_fns (str): Path to the neuron parameter file.

    Returns:
        list: List containing the unique hoc files.
    """
    hoc_files = []
    for neup_fn in neup_fns:
        neup = scp.build_parameters(neup_fn)
        hoc_files.append(neup["neuron"]["filename"])
    return list(set(hoc_files))

    
def _get_unique_landmark_fns_from_neups(neup_fns):
    """Get the unique landmark files from a list of neuron parameter files.

    Args:
        neup_fns (str): Path to the neuron parameter file.

    Returns:
        list: List containing the unique landmark files.
    """
    landmark_files = []
    for neup_fn in neup_fns:
        neup = scp.build_parameters(neup_fn)
        for landmark_file in neup["sim"]["recordingSites"]:
            landmark_files.append(landmark_file)
    return list(set(landmark_files))


def _generate_target_filenames(db, dir_name, file_list, hash_rename=True):
    if hash_rename:
        new_fns = [_hash_file_content(fn) for fn in file_list]
    else:
        new_fns = [os.path.basename(fn) for fn in file_list]
    return [
        os.path.join(db.basedir, dir_name, base_fn)
        for base_fn in new_fns
    ]


def _delayed_copy_transform_paramfiles_to_db(
    paramfile_hashmap_df,
    db,
    neup_path_column="path_neuron",
    neup_hash_column="hash_neuron",
    netp_path_column="path_network",
    netp_hash_column="hash_network",
):
    """Copy, transform and rename parameterfiles to a db.

    This function copies :ref:`cell_parameters_format`, :ref:`network_parameters_format`, :ref:`syn_file_format` files,
    and :ref:`con_file_format` files to the database.
    In the process, it renames each file to its hash and transforms the internal file references in the parameter files accordingly.

    Args:
        paramfile_hashmap_df (pd.DataFrame): DataFrame containing the filepaths and hashes.
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): The database to which the data should be added.
        path_column (str): Name of the column containing the filepaths.
        hash_column (str): Name of the column containing the hashes.
        transform_fun (function): Function to transform the parameter files.

    Returns:
        list: List of dask.delayed objects to copy the files.
    """

    cell_param_fns = paramfile_hashmap_df.drop_duplicates(subset=neup_hash_column)[
        neup_path_column
    ]
    netp_param_fns = paramfile_hashmap_df.drop_duplicates(subset=netp_hash_column)[
        netp_path_column
    ]
    syn_fns, con_fns = _get_unique_syncons_from_netps(netp_param_fns)
    hoc_fns = _get_unique_hoc_fns_from_neups(cell_param_fns)
    landmark_fns = _get_unique_landmark_fns_from_neups(cell_param_fns)
    logger.info("{} unique network parameter files".format(len(netp_param_fns)))
    logger.info("{} unique neuron parameter files".format(len(cell_param_fns)))
    logger.info("{} unique .hoc files".format(len(hoc_fns)))
    logger.info("{} unique .landmark files".format(len(landmark_fns)))
    logger.info("{} unique .syn files".format(len(syn_fns)))
    logger.info("{} unique .con files".format(len(con_fns)))

    # Target filenames in the database for each parameter file
    hoc_files_target_fns = _generate_target_filenames(db, HOC_DIR, hoc_fns, hash_rename=False)
    landmark_files_target_fns = _generate_target_filenames(db, RECSITES_DIR, landmark_fns, hash_rename=False)
    syn_files_target_fns = _generate_target_filenames(db, SYN_DIR, syn_fns, hash_rename=True)
    con_files_target_fns = _generate_target_filenames(db, CON_DIR, con_fns, hash_rename=True)
    cell_params_target_fns = _generate_target_filenames(db, NEUP_DIR, cell_param_fns, hash_rename=True)
    netp_params_target_fns = _generate_target_filenames(db, NETP_DIR, netp_param_fns, hash_rename=True)

    # create maps so we can transform file references in the parameter files, syn, and con files.
    syn_fn_map = dict(zip(syn_fns, syn_files_target_fns))
    con_fn_map = dict(zip(con_fns, con_files_target_fns))
    hoc_fn_map = dict(zip(hoc_fns, hoc_files_target_fns))
    recsites_fn_map = dict(zip(landmark_fns, landmark_files_target_fns))

        
    delayed_copy_hocs = [
        dask.delayed(shutil.copy)(fn, target_fn)
        for fn, target_fn in zip(hoc_fns, hoc_files_target_fns)
    ]
    delayed_copy_landmarks = [
        dask.delayed(shutil.copy)(fn, target_fn)
        for fn, target_fn in zip(landmark_fns, landmark_files_target_fns)
    ]
    delayed_copy_syns = [
        dask.delayed(_copy_and_transform_syn)(fn, target_fn, hoc_fn_map)
        for fn, target_fn in zip(syn_fns, syn_files_target_fns)
    ]
    delayed_copy_cons = [
        dask.delayed(_copy_and_transform_con)(fn, target_fn, syn_fn_map)
        for fn, target_fn in zip(con_fns, con_files_target_fns)
    ]
    delayed_copy_neups = [
        dask.delayed(_copy_and_transform_neuron_param)(fn, target_fn, hoc_fn_map, recsites_fn_map)
        for fn, target_fn in zip(cell_param_fns, cell_params_target_fns)
    ]
    delayed_copy_netps = [
        dask.delayed(_copy_and_transform_network_param)(
            fn, target_fn, syn_fn_map, con_fn_map
        )
        for fn, target_fn in zip(netp_param_fns, netp_params_target_fns)
    ]

    return (
        delayed_copy_hocs
        + delayed_copy_landmarks
        + delayed_copy_syns
        + delayed_copy_cons
        + delayed_copy_neups
        + delayed_copy_netps
    )


def load_param_files_from_db(db, sti):
    """Load the :ref:`cell_parameters_format` and :ref:`network_parameters_format` files from the database.

    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
            The database containing the parsed simulation results.
        sti (str):
            For which simulation trial index to load the parameter files.

    Returns:
        tuple: The :py:class:`~single_cell_parser.parameters.ParameterSet` objects for the cell and network.
    """
    import single_cell_parser as scp

    x = db["parameterfiles"].loc[sti]
    x_neu, x_net = x["hash_neuron"], x["hash_network"]
    neuf = db[NEUP_DIR].join(x_neu)
    netf = db[NETP_DIR].join(x_net)
    return scp.build_parameters(neuf), scp.build_parameters(netf)
