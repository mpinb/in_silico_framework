'''Parse simulation data generated with :py:mod:`simrun` for general purposes.

The output format of :py:mod:`simrun` is a nested folder structure with ``.csv`` and/or ``.npz`` files.
The voltage traces are written to a single ``.csv`` file (since the amount of timesteps is known in advance),
but the synapse and cell activation data is written to a separate file for each simulation trial (the amount 
of spikes and synapse activations is not known in advance).

This module provides functions to gather and parse this data in efficient data formats, namely pandas and dask dataframes.
After running :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.init`, a database is created containing
the following keys:

.. list-table::
    :header-rows: 1

    * - Key
      - Description
    * - ``simresult_path``
      - Filepath to the raw simulation output of :py:mod:`simrun`
    * - ``filelist``
      - List containing paths to all soma voltage trace files
    * - ``sim_trial_index``
      - The simulation trial indices as a pandas Series.
    * - ``metadata``
      - A metadata dataframe out of sim_trial_indices
    * - ``voltage_traces``
      - Dask dataframe containing the somatic voltage traces
    * - ``parameterfiles_cell_folder``
      - A :py:class:`~data_base.isf_data_base.IO.LoaderDumper.just_create_folder.ManagedFolder` 
        containing the :ref:`cell_parameters_format` file, renamed to its file hash.
    * - ``parameterfiles_network_folder``
      - A :py:class:`~data_base.isf_data_base.IO.LoaderDumper.just_create_folder.ManagedFolder`
        containing the :ref:`network_parameters_format` file, renamed to its file hash.
    * - ``parameterfiles``
      - A pandas dataframe containing the original paths of the parameter files and their hashes.
    * - ``synapse_activation``
      - Dask dataframe containing the parsed :ref:`syn_activation_format` data.
    * - ``cell_activation``
      - Dask dataframe containing the parsed :ref:`spike_times_format`.
    * - ``dendritic_recordings``
      - Subdatabase containing the membrane voltage at the recording sites specified in the 
        :ref:`cell_parameters_format` as a dask dataframe.
    * - ``dendritic_spike_times``
      - Subdatabase containing the spike times at the recording sites specified in the 
        :ref:`cell_parameters_format` as a dask dataframe.
    * - ``spike_times``
      - Dask dataframe containing the spike times of the postsynaptic cell for all trials.

After initialization, you can access the data from the data_base in the following manner::

    >>> db['synapse_activation']
    <synapse activation dataframe>
    >>> db['cell_activation']
    <cell activation dataframe>
    >>> db['voltage_traces']
    <voltage traces dataframe>
    >>> db['spike_times']
    <spike times dataframe>
    
If you intialize the database with ``rewrite_in_optimized_format=True`` (default), the keys are written as dask dataframes to the parquet format.
If ``rewrite_in_optimized_format=False`` instead, these keys are pickled dask dataframes, containing relative links to the
original ``.csv`` files. In essence, the dask dataframes contain the insturctions to build the dataframe, not the data itself.
This is useful for fast intermediate analysis. It is not intended and strongly discouraged for long term storage. 
Individual keys can afterwards be set to permanent, self-contained and efficient dask dataframes by calling 
:py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.load_simrun_general.optimize` on specific database
keys.

See also:
    :py:meth:`simrun.run_new_simulations._evoked_activity` for more information on the raw output format of :py:mod:`simrun`.
    :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.init` for the initialization of the database.
'''

import os, glob, shutil, fnmatch, hashlib, six, dask, compatibility, scandir, warnings
import numpy as np
import pandas as pd
import dask.dataframe as dd
import single_cell_parser as scp
import single_cell_parser.analyze as sca
from data_base.isf_data_base import ISFDataBase
from data_base.isf_data_base.IO.LoaderDumper import (
    pandas_to_pickle,
    to_cloudpickle, 
    to_pickle, 
    pandas_to_parquet, 
    get_dumper_string_by_dumper_module, 
    dask_to_parquet)
from data_base.exceptions import DataBaseException
from data_base.isf_data_base.IO.roberts_formats import read_pandas_synapse_activation_from_roberts_format as read_sa
from data_base.isf_data_base.IO.roberts_formats import read_pandas_cell_activation_from_roberts_format as read_ca
from data_base.analyze.spike_detection import spike_detection
# from data_base.analyze.burst_detection import burst_detection
from data_base.utils import mkdtemp, chunkIt, unique, silence_stdout
import logging
logger = logging.getLogger("ISF").getChild(__name__)

DEFAULT_DUMPER = to_cloudpickle
OPTIMIZED_PANDAS_DUMPER = pandas_to_parquet
OPTIMIZED_DASK_DUMPER = dask_to_parquet

#-----------------------------------------------------------------------------------------
# 1: Create filelist containing paths to all soma voltage trace files
#-----------------------------------------------------------------------------------------

def make_filelist(directory, suffix='vm_all_traces.csv'):
    """Generate a list of all files with :paramref:`suffix` in the specified directory.
    
    Simulation results from :py:mod:`simrun` are stored in a nested folder structure, and spread
    across multiple files. The first step towards parsing them is to generate a list of all files
    containing the data we are interested in.
    
    Args:
        directory (str): 
            Path to the directory containing the simulation results.
            In general, this directory will contain a nested subdirectory structure.
        suffix (str):
            The suffix of the data files.
            Default is ``'vm_all_traces.csv'`` for somatic voltage traces.
        
    Returns:
        list: List of all soma voltage trace files in the specified directory.
    """
    matches = []
    for root, dirnames, filenames in scandir.walk(directory):
        for filename in fnmatch.filter(filenames, '*' + suffix):
            dummy = os.path.join(root, filename)
            if '_running' in dummy:
                logging.info('skip incomplete simulation: {}'.format(dummy))
            else:
                matches.append(os.path.relpath(dummy, directory))

    if len(matches) == 0:
        raise ValueError(
            "Did not find any '*{suffix}'-files. Filelist empty. Abort initialization."
            .format(suffix=suffix))
    return matches


#-----------------------------------------------------------------------------------------
# 2: Generate dask dataframe containing the voltagetraces
#-----------------------------------------------------------------------------------------
#    This dataframe then contains the sim_trial_index

@dask.delayed
def read_voltage_traces_from_files_pandas(prefix, fnames):
    """Reads a list of **multiple** voltage trace files and parses it to a single pandas dataframe.
    
    The delayed version of this method is used to construct a dask dataframe containing the voltage traces
    in :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.read_voltage_traces_by_filenames`.
    Each singular file is read using :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.read_voltage_traces_from_file`.
    
    Args:
        prefix (str): Path to the directory containing the simulation results.
        fnames (list): List of filenames pointing to voltage trace files.
        
    Returns:
        pandas.DataFrame: A pandas dataframe containing the voltage traces.
        
    See also:
        :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.read_voltage_traces_by_filenames`.
    """
    dfs = [read_voltage_traces_from_file(prefix, fname) for fname in fnames]
    return pd.concat(dfs, axis=0)


def read_voltage_traces_from_file(prefix, fname):
    '''Reads a **single** voltage traces file as generated by the simrun package.
    
    Infers the data format of the voltage traces file from the file extension (either ``.csv`` or ``.npz``).
    Reads them in and parses it to a pandas datafram, containing the original path and simulation trial as an index.
    
    Example:

        >>> simrun_result_fn = 'path/to/sim_result/vm_all_traces.csv'
        >>> with open(simrun_result_fn, 'r') as file: print(file.read())
        # This is an example for a .csv file (so not .npz)
        t	Vm run 00	Vm run 01	
        100.0	-61.4607218758	-55.1366909604
        100.025	-61.4665809176	-55.1294343391
        100.05	-61.4735021526	-55.1223216173
        ...
        >>> read_voltage_traces_from_file(prefix="path/to/sim_result", v_fn)
        sim_trial_index                         100.0         100.025          ...
        path/to/sim_result/000000    -61.4607218758 -61.4665809176   ...
        path/to/sim_result/000001    -55.1366909604 -55.1294343391   ...
        ...
    
    Important:
        The simulation trial index is inferred from the filename of the voltage traces file.
        Ideally, this path should contain a unique identifier, containing e.g. the date, 
        seed and/or the PID of the simulation run.
    
    Args:
        prefix (str): Path to the directory containing the simulation results.
        fname (str): Filename pointing to a voltage trace file. The file can be in either ``.csv`` or ``.npz`` format.
    
    Returns:
        pd.DataFrame: A pandas dataframe containing the voltage traces.
        
    See also:
        :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.read_voltage_traces_from_csv` and
        :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.read_voltage_traces_from_npz`
    '''
    if fname.endswith('.csv'):
        return read_voltage_traces_from_csv(prefix, fname)
    if fname.endswith('.npz'):
        return read_voltage_traces_from_npz(prefix, fname)


read_voltage_traces_from_file_delayed = dask.delayed(
    read_voltage_traces_from_file)


def read_voltage_traces_from_csv(prefix, fname):
    '''Reads a single :ref:`voltage_traces_csv_format` file as generated by the :py:mod:`simrun` package.
    
    Args:
        prefix (str): Path to the directory containing the simulation results.
        fname (str): Filename pointing to a voltage trace file. The file is expected to be in ``.csv`` format.
        
    See also:
        :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.read_voltage_traces_from_file`
    
    Returns:
        pd.DataFrame: A pandas dataframe containing the voltage traces.
    '''
    full_fname = os.path.join(prefix, fname)
    with open(full_fname) as f:
        data = np.loadtxt(f, skiprows=1, unpack=True, dtype='float64')
    #special case: if only one row is contained in data, this has to be a column vector
    if len(data.shape) == 1:
        data = data.reshape(len(data), 1)
    t = data[0]
    data = data[1:]
    # In case the simulation trial indices are not consecutive
    INDICES = sorted([int(f.split('_')[1][3:]) for f in os.listdir(os.path.dirname(full_fname)) if 'synapses' in f])
    index = [
        str(os.path.join(os.path.dirname(fname),
                         str(index).zfill(6))) for index in INDICES]  ##this will be the sim_trail_indexndex = [
    #print index
    df = pd.DataFrame(data, columns=t)
    df['sim_trial_index'] = index
    df.set_index('sim_trial_index', inplace=True)
    return df


def read_voltage_traces_from_npz(prefix, fname):
    '''Reads a single :ref:`voltage_traces_npz_format` file as generated by the simrun package.
    
    Args:
        prefix (str): Path to the directory containing the simulation results.
        fname (str): Filename pointing to a voltage trace file. The file is expected to be in ``.npz`` format.
        
    See also:
        :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.read_voltage_traces_from_file`
    '''
    warnings.warn(
        "You are loading voltage traces from npz files. This only works, if you are using a fixed stepsize of 0.025 ms"
    )
    data = np.load(os.path.join(prefix, fname))['arr_0']
    data = np.transpose(data)
    vt = data[1:, :]
    t = np.array([0.025 * n for n in range(data.shape[1])])
    sim_trial_index_base = os.path.dirname(
        fname)  #os.path.dirname(os.path.relpath(prefix, fname))
    index = [
        str(os.path.join(sim_trial_index_base,
                         str(index).zfill(6))) for index in range(len(vt))
    ]  ##this will be the sim_trial_index

    df = pd.DataFrame(vt, columns=t)
    df['sim_trial_index'] = index
    df.set_index('sim_trial_index', inplace=True)

    return df


def read_voltage_traces_by_filenames(
    prefix,
    fnames,
    divisions=None,
    repartition=None):
    '''Reads a list of **multiple** voltage trace files and parses it to a dask dataframe.
    
    Also sets the database key ``sim_trial_index`` to contain the paths of the simulation trials.
    This is the default way of constructing a dask dataframe containing the voltage traces.
    
    Args:
        prefix (str): Path to the directory containing the simulation results.
        fnames (list): list of filenames pointing to voltage trace files
        divisions (list): list of divisions for the dask dataframe. Default is None, letting Dask handle it.
        repartition (bool): If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
    
    Returns: 
        dask.DataFrame: A dask dataframe containing the voltage traces.
        
    See also:
        :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.read_voltage_traces_from_file`
        is used to read in each single voltage trace file. Consult this method for more information on how the data format
        is parsed.
    '''
    assert repartition is not None
    fnames = sorted(fnames)
    if repartition and len(fnames) > 10000:
        fnames_chunks = chunkIt(fnames, 5000)
        delayeds = [
            read_voltage_traces_from_files_pandas(prefix, fnames_chunk)
            for fnames_chunk in fnames_chunks
        ]
    else:
        delayeds = [
            read_voltage_traces_from_file_delayed(prefix, fname)
            for fname in fnames
        ]
    if divisions is not None:
        assert len(divisions) - 1 == len(delayeds)
    meta = read_voltage_traces_from_file(prefix, fnames[0]).head()
    ddf = dd.from_delayed(delayeds, meta=meta, divisions=divisions)
    return ddf


def get_voltage_traces_divisions_by_metadata(metadata, repartition=None):
    """Find the division indices based on the metadata.
    
    The trial numbers always augment, so for each partition, the lowest trial number is
    the first entry of that partition. This way, the division indices can be inferred
    by simply finding the lowest trial number in each partition.
    
    Args:
        metadata (pd.DataFrame): Metadata dataframe containing the simulation trial indices.
        repartition (bool): If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
        
    Returns:
        tuple: Tuple containing the divisions for the voltage traces dataframe.
    """
    assert repartition is not None
    divisions = metadata[metadata.trialnr == min(metadata.trialnr)]
    divisions = list(divisions.sim_trial_index)
    if len(divisions) > 10000 and repartition:
        divisions = [d[0] for d in chunkIt(divisions, 5000)]
    return tuple(divisions + [metadata.iloc[-1].sim_trial_index])

#-----------------------------------------------------------------------------------------
# 3: read out the sim_trial_index from the soma voltage traces dask dataframe
#-----------------------------------------------------------------------------------------

# this is expensive and might be optimized

# this is done directly in the _build function below

#-----------------------------------------------------------------------------------------
# 4: generate metadata dataframe out of sim_trial_indices
#-----------------------------------------------------------------------------------------

@dask.delayed
def create_metadata_parallelization_helper(sim_trial_index, simresult_path):
    """Parallelize creating metadata across multiple simulation trials.
    
    See also:
        This is used in 
        :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.create_metadata`.
    
    Args:
        sim_trial_index (pd.Series): A pandas series containing the sim_trial_index.
        simresult_path (str): Path to the simulation results folder.
        
    Returns:
        pd.DataFrame: A pandas dataframe containing the metadata.
    """

    def determine_zfill_used_in_simulation(globstring):
        '''The number of digits like 0001 or 000001 is not consitent accross 
        simulation results. This function takes care of this.
        
        Args:
            globstring (str): A string containing a glob pattern.
            
        Returns:
            int: The number of digits used in the simulation results.
        '''
        #print globstring
        ret = len(
            os.path.basename(
                glob.glob(globstring)[0]).split('_')[1].lstrip('run'))
        return ret

    def voltage_trace_file_list(x):
        '''Returns part of the metadata dataframe.
        
        This function extracts the path, trial number, and filename of the voltage traces file.
        
        Args:
            x (pd.Series): A pandas series containing the sim_trial_index.
            
        Returns:
            pd.Series: A pandas series containing the path, trial number, and filename of the voltage traces file.
        '''
        path = x.sim_trial_index
        path, trialnr = os.path.split(path)
        voltage_traces_file_name = os.path.basename(path)
        voltage_traces_file_name = voltage_traces_file_name.split('_')[-1] \
                                        + '_vm_all_traces.csv'

        return pd.Series({'path': path, \
                          'trialnr': trialnr, \
                          'voltage_traces_file_name': voltage_traces_file_name})

    def synaptic_file_list(x):
        '''Returns part of the metadata dataframe.
        
        Extracts the filename of the synapse activation file.
        
        Args:
            x (pd.Series): A pandas series containing the ``trialnr``.
            
        Returns:
            pd.Series: A pandas series containing the filename of the synapse activation file.
        '''
        testpath = os.path.join(simresult_path, os.path.dirname(list(sim_trial_index.sim_trial_index)[0]), '*%s*.csv')
        zfill_synapses = determine_zfill_used_in_simulation(testpath %'synapses')
        synapses_file_name = "simulation_run%s_synapses.csv" % str(int(x.trialnr)).zfill(zfill_synapses)
        return pd.Series({'synapses_file_name': synapses_file_name})

    def cells_file_list(x):
        '''Returns part of the metadata dataframe.
        
        Extracts the filename of the cell activation file.
        
        Args:
            x (pd.Series): A pandas series containing the ``trialnr``.
            
        Returns:
            pd.Series: A pandas series containing the filename of the cell activation file.
        '''
        testpath = os.path.join(simresult_path, os.path.dirname(list(sim_trial_index.sim_trial_index)[0]), '*%s*.csv')
        zfill_cells = determine_zfill_used_in_simulation(testpath % 'cells')
        cells_file_name = "simulation_run%s_presynaptic_cells.csv" % str(int(x.trialnr)).zfill(zfill_cells)
        return pd.Series({'cells_file_name': cells_file_name})

    path_trialnr = sim_trial_index.apply(voltage_trace_file_list, axis=1)
    sim_trial_index_complete = pd.concat((sim_trial_index, path_trialnr), axis=1)
    
    try:
        synaptic_files = path_trialnr.apply(synaptic_file_list, axis=1)
        sim_trial_index_complete = pd.concat((sim_trial_index_complete, synaptic_files), axis=1)
    except IndexError:  # special case if synapse activation data is not in the simulation folder
        warnings.warn('Could not find synapse activation files')
    try:
        cell_files = path_trialnr.apply(cells_file_list, axis=1)
        sim_trial_index_complete = pd.concat((sim_trial_index_complete, cell_files), axis=1)
    except IndexError:
        warnings.warn('could not find cell activation files')
    return sim_trial_index_complete


def create_metadata(db):
    """Generate metadata out of a pd.Series containing the sim_trial_index.
    
    Expands the sim_trial_index to a pandas Series containing the path, trial number, 
    and filename of the voltage traces file.
    
    Args:
        sim_trial_index (pd.Series): A pandas series containing the sim_trial_index.
        simresult_path (str): Path to the simulation results folder.
        
    Returns:
        pd.DataFrame: A pandas dataframe containing the metadata.
    """
    simresult_path = db['simresult_path']
    sim_trial_index = list(db['sim_trial_index'])
    sim_trial_index = pd.DataFrame(dict(sim_trial_index=list(sim_trial_index)))
    sim_trial_index_dask = dask.dataframe.from_pandas(sim_trial_index,
                                                      npartitions=5000)
    sim_trial_index_delayed = sim_trial_index_dask.to_delayed()
    sim_trial_index_complete = [
        create_metadata_parallelization_helper(d, simresult_path)
        for d in sim_trial_index_delayed
    ]
    sim_trial_index_complete = dask.compute(sim_trial_index_complete)
    return pd.concat(
        sim_trial_index_complete[0]
    )  # create_metadata_parallelization_helper(sim_trial_index, simresult_path)


#-----------------------------------------------------------------------------------------
# 5: rewrite synapse and cell activation data to
#    a  format that can be read by pandas, and attach sim_trial_index to it
#-----------------------------------------------------------------------------------------

from data_base.IO.roberts_formats import _max_commas

def get_max_commas(paths):
    """Get the maximum amount of delimiters across many files.
    
    Some data formats have a varying amount of commas in the synapse and cell 
    activation files, reflecting e.g. different amounts of spikes per cell.
    This can not be padded during simulation, since it is not known what the maximum
    amount of e.g. spikes will be.
    This function determines the maximum amount of delimiters across all files post-hoc,
    so that the data can be padded out and read in.
    
    Args:
        paths (list): List of paths to the synapse and cell activation files.
        
    Returns:
        int: The maximum amount of delimiters across all files.
    """
    @dask.delayed
    def max_commas_in_chunk(filepaths):
        '''determine maximum number of delimiters (\t or ,) in files
        specified by list of filepaths'''
        n = 0
        for path in filepaths:
            n = max(n, _max_commas(path))
        return n

    filepath_chunks = chunkIt(
        paths, 3000
    )  # count commas in max 300 processes at once. Arbitrary but reasonable.
    max_commas = [max_commas_in_chunk(chunk) for chunk in filepath_chunks]
    max_commas = dask.delayed(max_commas).compute()
    return max(max_commas)


#-----------------------------------------------------------------------------------------
# 6: load dendritic voltage traces
#-----------------------------------------------------------------------------------------

def load_dendritic_voltage_traces_helper(
    db,
    suffix,
    divisions=None,
    repartition=None):
    """Read the dendritic voltage traces of a single recording site across multiple simulation trials.
    
    This method constructs a list of all filenames corresponding to a single recording site and reads them in
    using :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.read_voltage_traces_by_filenames`.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): 
            The target database that should contain the parsed simulation results.
        suffix (str):
            The suffix of the dendritic voltage trace files.
            This suffix is used to construct the filenames of the dendritic voltage trace files.
        divisions (list):
            List of divisions for the dask dataframe.
            Default is None, letting Dask handle it.
        repartition (bool):
            If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
            
    Returns:
        dask.DataFrame: A dask dataframe containing the dendritic voltage traces.
    """
    assert repartition is not None
    m = db['metadata']
    if not suffix.endswith('.csv'):
        suffix = suffix + '.csv'
    if not suffix.startswith('_'):
        suffix = '_' + suffix
    #print os.path.join(db['simresult_path'], m.iloc[0].path, m.iloc[0].path.split('_')[-1] + suffix)
    
    # old naming convention
    if os.path.exists(
            os.path.join(db['simresult_path'], m.iloc[0].path,
                         m.iloc[0].path.split('_')[-1] + suffix)):
        fnames = [
            os.path.join(x.path,
                         x.path.split('_')[-1] + suffix)
            for index, x in m.iterrows()
        ]
    
    # new-ish naming convention
    elif os.path.exists(
            os.path.join(db['simresult_path'], m.iloc[0].path,
                         'seed_' + m.iloc[0].path.split('_')[-1] + suffix)):
        fnames = [
            os.path.join(x.path, 'seed_' + x.path.split('_')[-1] + suffix)
            for index, x in m.iterrows()
        ]
    
    # brand new naming convention
    elif os.path.exists(
            os.path.join(
                db['simresult_path'], m.iloc[0].path,
                m.iloc[0].path.split('_')[-2] + '_' +
                m.iloc[0].path.split('_')[-1] + suffix)):
        fnames = [
            os.path.join(
                x.path,
                x.path.split('_')[-2] + '_' + x.path.split('_')[-1] + suffix)
            for index, x in m.iterrows()
        ]
    
    # print(suffix)
    fnames = unique(fnames)
    ddf = read_voltage_traces_by_filenames(
        db['simresult_path'],
        fnames,
        divisions=divisions,
        repartition=repartition)
    return ddf


def load_dendritic_voltage_traces(db, suffix_key_dict, repartition=None):
    """Load the voltage traces from dendritic recording sites.
    
    Dendritic recording sites are defined in the cell :ref:`` files
    (under the key ``sim.recordingSites``).
    The voltage traces for each recording site are read with 
    :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.load_dendritic_voltage_traces_helper`.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
            The target database that should contain the parsed simulation results.
        suffix_key_dict (dict):
            Dictionary containing the suffixes of the dendritic voltage trace files.
            The keys are the labels of the recording sites, and the values are the suffixes of the dendritic voltage trace files.
        repartition (bool):
            If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
            
    Returns:
        dict: Dictionary containing the dask dataframes of the dendritic voltage traces.
    
    """
    out = {}
    divisions = db['voltage_traces'].divisions
    # suffix_key_dict is of form: {recSite.label:  recSite.label + '_vm_dend_traces.csv'}
    for key in suffix_key_dict:
        out[key] = \
            load_dendritic_voltage_traces_helper(
                db,
                suffix_key_dict[key],
                divisions=divisions,
                repartition=repartition)
    return out


#-----------------------------------------------------------------------------------------
# 7: load parameterfiles
#-----------------------------------------------------------------------------------------
def get_file(self, suffix):
    """Get the unique file in the current directory with the specified suffix.
    
    This method does not recurse into subdirectories.
    
    Args:
        self (str): Path to the directory.
        suffix (str): Suffix of the files to be found.
        
    Returns:
        str: Path to the file with the specified suffix.
        
    Raises:
        ValueError: If no file with the specified suffix is found.
        ValueError: If multiple files with the specified suffix are found.
    """
    l = [f for f in os.listdir(self) if f.endswith(suffix)]
    if len(l) == 0:
        raise ValueError(
            'The folder {} does not contain a file with the suffix {}'.format(
                self, suffix))
    elif len(l) > 1:
        raise ValueError(
            'The folder {} contains several files with the suffix {}'.format(
                self, suffix))
    else:
        return os.path.join(self, l[0])


def generate_param_file_hashes(simresult_path, sim_trial_index):
    """Generate a DataFrame containing the paths and hashes of :ref:`cell_parameters_format` and :ref:`network_parameters_format` files.
    
    Args:
        simresult_path (str): Path to the simulation results folder.
        sim_trial_index (array): array of sim_trial_indices to generate paramfiles for.
        
    Returns:
        list: list of dask.delayed objects to calculate the pd.DataFrame objects containing the paths to the parameter files and their hashes.
    """
    logging.info("find unique parameterfiles")

    def fun(x):
        sim_trial_folder = os.path.dirname(x.sim_trial_index)
        identifier = os.path.basename(sim_trial_folder).split('_')[-1]
        return sim_trial_folder, identifier

    def fun_network(x):
        sim_trial_folder, identifier = fun(x)
        #return os.path.join(simresult_path, sim_trial_folder, identifier + '_network_model.param')
        return get_file(os.path.join(simresult_path, sim_trial_folder),
                        '_network_model.param')

    def fun_neuron(x):
        sim_trial_folder, identifier = fun(x)
        # return os.path.join(simresult_path, sim_trial_folder, identifier + '_neuron_model.param')
        return get_file(os.path.join(simresult_path, sim_trial_folder),
                        '_neuron_model.param')

    @dask.delayed
    def _helper(df):
        ## todo: crashes if specified folder directly contains the param files
        ## and not a subfolder containing the param files
        df['path_neuron'] = df.apply(lambda x: fun_neuron(x), axis=1)
        df['path_network'] = df.apply(lambda x: fun_network(x), axis=1)
        df['hash_neuron'] = df['path_neuron'].map(
            lambda x: hashlib.md5(open(x, 'rb').read()).hexdigest())
        df['hash_network'] = df['path_network'].map(
            lambda x: hashlib.md5(open(x, 'rb').read()).hexdigest())
        return df

    df = pd.DataFrame(dict(sim_trial_index=list(sim_trial_index)))
    ddf = dd.from_pandas(df, npartitions=3000).to_delayed()
    delayeds = [_helper(df) for df in ddf]
    return delayeds  # dask.delayed(delayeds)


#####################################
# step seven point one: replace paths in param files with relative dbpaths
#####################################
from data_base.dbopen import create_db_path

def create_db_path_print(path, replace_dict={}):
    """:skip-doc:"""
    ## replace_dict: todo
    try:
        return create_db_path(path), True
    except DataBaseException as e:
        # print e
        return path, False


def cell_param_to_dbpath(neuron):
    """
    :skip-doc:
    
    Used as a :paramref:`transform_fun` in 
    :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.write_param_files_to_folder`.
    """
    flag = True
    neuron['neuron']['filename'], flag_ = create_db_path_print(
        neuron['neuron']['filename'])
    flag = flag and flag_
    rec_sites = [
        create_db_path_print(p) for p in neuron['sim']['recordingSites']
    ]
    neuron['sim']['recordingSites'] = [r[0] for r in rec_sites]
    flag = flag and all([r[1] for r in rec_sites])
    if 'channels' in neuron['NMODL_mechanisms']:
        neuron['NMODL_mechanisms']['channels'], flag = create_db_path_print(
            neuron['NMODL_mechanisms']['channels'])
        flag = flag and flag_
    return flag


def network_param_to_dbpath(network):
    """
    :skip-doc:
    """
    flag = True
    network['NMODL_mechanisms']['VecStim'], flag_ = create_db_path_print(
        network['NMODL_mechanisms']['VecStim'])
    flag = flag and flag_
    network['NMODL_mechanisms']['synapses'], flag_ = create_db_path_print(
        network['NMODL_mechanisms']['synapses'])
    flag = flag and flag_
    for k in list(network['network'].keys()):
        if k == 'network_modify_functions':
            continue
        network['network'][k]['synapses'][
            'connectionFile'], flag_ = create_db_path_print(
                network['network'][k]['synapses']['connectionFile'])
        flag = flag and flag_
        network['network'][k]['synapses'][
            'distributionFile'], flag_ = create_db_path_print(
                network['network'][k]['synapses']['distributionFile'])
        flag = flag and flag_
    return flag


@dask.delayed
def parallel_copy_helper(df, transform_fun=None):
    """:skip-doc:"""
    for name, value in df.iterrows():
        param = scp.build_parameters(value.from_)
        #         print 'ready to transform'
        transform_fun(param)
        param.save(value.to_)

        # if transform_fun is None:
        #     shutil.copy(value.from_, value.to_)
        # else:
        #     param = scp.build_parameters(value.from_)
        #     print 'ready to transform'
        #     transform_fun(param)
        #     param.save(value.to_)


def write_param_files_to_folder(
    df,
    folder,
    path_column,
    hash_column,
    transform_fun=None):
    """Write the parameter files to a specified folder.
    
    Given a dataframe containing filepaths and their respective hashes,
    this method copies the files to the specified :paramref:`folder`.
    The files will be copied to the folder and renamed according to their hash.
    
    Args:
        df (pd.DataFrame): DataFrame containing the filepaths and hashes.
        folder (str): Path to the folder where the files should be copied to.
        path_column (str): Name of the column containing the filepaths.
        hash_column (str): Name of the column containing the hashes.
        transform_fun (function): Function to transform the parameter files.
        
    Returns:
        list: List of dask.delayed objects to copy the files.
    """
    logging.info("move parameterfiles")
    df = df.drop_duplicates(subset=hash_column)
    logging.info('number of parameterfiles: {}'.format(len(df)))
    df2 = pd.DataFrame()
    df2['from_'] = df[path_column]
    df2['to_'] = df.apply(
        lambda x: os.path.join(folder, x[hash_column]),
        axis=1)
    ddf = dd.from_pandas(df2, npartitions=200).to_delayed()
    return [parallel_copy_helper(d, transform_fun=transform_fun) for d in ddf]


###########################################################################################
# Build database using the helper functions above
###########################################################################################
def _build_core(db, repartition=None, metadata_dumper=pandas_to_parquet):
    """Parse the essential simulation results and add it to :paramref:`db`.
    
    The following data is parsed and added to the database: 
    
    - filelist
    - somatic voltage traces
    - simulation trial index
    - metadata
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): The database to which the data should be added.
        repartition (bool): If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
        metadata_dumper (function): Function to dump the metadata to disk. Default is :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.pandas_to_parquet`.
        
    Returns:
        None
    """
    assert repartition is not None
    logging.info('---building data base core---')
    logging.info('generate filelist ...')

    # 1. Generate filelist containing paths to all soma voltage trace files
    try:
        filelist = make_filelist(db['simresult_path'], 'vm_all_traces.csv')
    except ValueError:
        filelist = make_filelist(db['simresult_path'], 'vm_all_traces.npz')
    db['filelist'] = filelist

    # 2. Generate dask dataframe containing the voltagetraces
    logging.info('generate voltage traces dataframe...')
    # vt = read_voltage_traces_by_filenames(db['simresult_path'], db['file_list'])
    vt = read_voltage_traces_by_filenames(
        db['simresult_path'], 
        filelist,
        repartition=repartition)
    db.set('voltage_traces', vt, dumper=DEFAULT_DUMPER)
    
    # 3. Read out the sim_trial_index from the soma voltage traces dask dataframe
    logging.info('generate index ...')
    db['sim_trial_index'] = db['voltage_traces'].index.compute()

    # 4. Generate metadata dataframe out of sim_trial_indices
    logging.info('generate metadata ...')
    db.set('metadata', create_metadata(db), dumper=metadata_dumper)

    logging.info('add divisions to voltage traces dataframe')
    vt.divisions = get_voltage_traces_divisions_by_metadata(
        db['metadata'], repartition=repartition)
    db.set('voltage_traces', vt, dumper=DEFAULT_DUMPER)

    
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
        logging.info('counting commas')
        max_commas = get_max_commas(paths) + 1
        #print max_commas
        logging.info('generate dataframe')
        path_sti_tuples = list(zip(paths, list(db['sim_trial_index'])))
        if repartition and len(paths) > 10000:
            path_sti_tuples = chunkIt(path_sti_tuples, n_chunks)
            delayeds = [
                file_reader_fun(list(zip(*x))[0],
                                list(zip(*x))[1], max_commas)
                for x in path_sti_tuples
            ]
            divisions = [x[0][1] for x in path_sti_tuples
                        ] + [path_sti_tuples[-1][-1][1]]
        else:
            delayeds = [
                file_reader_fun(p, sti, max_commas)
                for p, sti in path_sti_tuples
            ]
            divisions = [x[1] for x in path_sti_tuples
                        ] + [path_sti_tuples[-1][1]]
        ddf = dd.from_delayed(delayeds,
                              meta=delayeds[0].compute(scheduler="threads"),
                              divisions=divisions)
        logging.info('save dataframe')
        db.set(key, ddf, dumper=dumper)

    simresult_path = db['simresult_path']
    if simresult_path[-1] == '/' and len(simresult_path) > 1:
        simresult_path = simresult_path[:-1]

    m = db['metadata'].reset_index()
    if 'synapses_file_name' in m.columns:
        logging.info('---building synapse activation dataframe---')
        paths = list(simresult_path + '/' + m.path + '/' + m.synapses_file_name)
        template('synapse_activation', paths,
                 dask.delayed(read_sa, traverse=False), DEFAULT_DUMPER)
    if 'cells_file_name' in m.columns:
        logging.info('---building cell activation dataframe---')
        paths = list(simresult_path + '/' + m.path + '/' + m.cells_file_name)
        template('cell_activation', paths,
                 dask.delayed(read_ca, traverse=False), DEFAULT_DUMPER)


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
    param_files = glob.glob(os.path.join(db['parameterfiles_cell_folder'],
                                         '*'))
    param_files = [p for p in param_files if not p.endswith(('Loader.pickle', 'Loader.json', 'metadata.json'))]
    logging.info(len(param_files))
    rec_sites = []
    for param_file in param_files:
        neuronParameters = scp.build_parameters(param_file)
        rec_site = neuronParameters.sim.recordingSites
        rec_sites.append(tuple(rec_site))
    rec_sites = set(rec_sites)
    #print param_files
    if len(rec_sites) > 1:
        raise NotImplementedError(
            "Cannot initialize database with dendritic recordings if"\
            +" the cell parameter files differ in the landmarks they specify for the recording sites.")
    #############
    # the following code is adapted from simrun
    #############
    neuronParameters = scp.build_parameters(param_files[0])
    rec_sites = neuronParameters.sim.recordingSites
    cellParam = neuronParameters.neuron
    with silence_stdout:
        cell = scp.create_cell(cellParam, setUpBiophysics=True)
    recSiteManagers = [
        sca.RecordingSiteManager(recFile, cell) for recFile in rec_sites
    ]
    out =  {recSite.label:  recSite.label + '_vm_dend_traces.csv'  \
            for RSManager in recSiteManagers \
            for recSite in RSManager.recordingSites}
    return out


def _build_dendritic_voltage_traces(db, suffix_dict=None, repartition=None):
    """Load dendritic voltage traces and add them to the database under the key ``dendritic_recordings``.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): The database to which the data should be added.
        suffix_dict (dict): Dictionary containing the suffixes of the dendritic voltage trace files. 
            Default is None, and they are inferred from the cell parameter files.
        repartition (bool): If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
        
    Returns:
        None    
    """
    assert repartition is not None
    logging.info('---building dendritic voltage traces dataframes---')

    if suffix_dict is None:
        suffix_dict = _get_rec_site_managers(db)

    out = load_dendritic_voltage_traces(
        db,
        suffix_dict,
        repartition=repartition)
    if not 'dendritic_recordings' in list(db.keys()):
        db.create_sub_db('dendritic_recordings')

    sub_db = db['dendritic_recordings']

    for recSiteLabel in list(suffix_dict.keys()):
        sub_db.set(recSiteLabel, out[recSiteLabel], dumper=DEFAULT_DUMPER)
    #db.set('dendritic_voltage_traces_keys', out.keys(), dumper = DEFAULT_DUMPER)


def _build_param_files(db, client):
    """Parse parameterfiles and add them to the database.
    
    Paremeterfiles are the files containing the parameters of the cell and network models.
    These files are copied to the database in the subdirectories ``"parameterfiles_cell_folder"`` 
    and ``"parameterfiles_network_folder"`` and renamed to their hash.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): 
            The database to which the parameterfiles should be added.
        client (:py:class:`~dask.distributed.client.Client`): The Dask client to use for parallel computation.
        
    Returns:
        None. Sets the keys ``parameterfiles_cell_folder`` and ``parameterfiles_network_folder`` in the database.
    
    See also:
        The :ref:`cell_parameters_format` and :ref:`network_parameters_format` formats.
    """
    logging.info('---moving parameter files---')
    ds = generate_param_file_hashes(
        db['simresult_path'],
        db['sim_trial_index'])
    futures = client.compute(ds)
    result = client.gather(futures)
    df = pd.concat(result)
    df.set_index('sim_trial_index', inplace=True)
    if 'parameterfiles_cell_folder' in list(db.keys()):
        del db['parameterfiles_cell_folder']
    if 'parameterfiles_network_folder' in list(db.keys()):
        del db['parameterfiles_network_folder']
    
    ds = write_param_files_to_folder(
        df,
        db.create_managed_folder('parameterfiles_cell_folder'),
        'path_neuron',
        'hash_neuron',
        transform_fun=cell_param_to_dbpath)
    client.gather(client.compute(ds))
    
    ds = write_param_files_to_folder(
        df, 
        db.create_managed_folder('parameterfiles_network_folder'),
        'path_network', 
        'hash_network', 
        network_param_to_dbpath)
    client.gather(client.compute(ds))

    db.set('parameterfiles', df, dumper=pandas_to_parquet)


def init(
        db, 
        simresult_path,
        core=True, 
        voltage_traces= True, 
        synapse_activation = True,
        dendritic_voltage_traces = True, 
        parameterfiles = True,
        spike_times = True,  
        burst_times = False, \
        repartition = True, 
        scheduler = None, 
        rewrite_in_optimized_format = True,
        dendritic_spike_times = True, 
        dendritic_spike_times_threshold = -30.,
        client = None, 
        n_chunks = 5000, 
        dumper = OPTIMIZED_PANDAS_DUMPER):
    '''Initialize a database with simulation data.
    
    Use this function to load simulation data generated with the simrun module 
    into a :py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`.
    
    Args:
        core (bool, optional):
            Parse and write the core data to the database: voltage traces, metadata, sim_trial_index and filelist.
            See also: :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general._build_core`
        voltage_traces (bool, optional):
            Parse and write the somatic voltage traces to the database.
        spike_times (bool, optional):
            Parse and write the spike times into the database.
            See also: :py:meth:`data_base.analyze.spike_detection.spike_detection`
        dendritic_voltage_traces (bool, optional):
            Parse and write the dendritic voltage traces to the database.
            See also: :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general._build_dendritic_voltage_traces`
        dendritic_spike_times (bool, optional):
            Parse and write the dendritic spike times to the database.
            See also: :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.add_dendritic_spike_times`
        dendritic_spike_times_threshold (float, optional):
            Threshold for the dendritic spike times in mV. Default is :math:`-30`.
            See also: :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.add_dendritic_spike_times`
        synapse_activation (bool, optional):
            Parse and write the synapse activation data to the database.
            See also: :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general._build_synapse_activation`
        parameterfiles (bool, optional):
            Parse and write the parameterfiles to the database.
            See also: :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general._build_param_files`
        rewrite_in_optimized_format (bool, optional): 
            If True (default): data is converted to a high performance binary 
            format and makes unpickling more robust against version changes of third party libraries. 
            Also, it makes the database self-containing, i.e. you can move it to another machine or 
            subfolder and everything still works. Deleting the data folder then would (should) not cause 
            loss of data. 
            If False: the db only contains links to the actual simulation data folder 
            and will not work if the data folder is deleted or moved or transferred to another machine 
            where the same absolute paths are not valid.
        repartition (bool, optional):
            If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
        n_chunks (int, optional):
            Number of chunks to split the :ref:`syn_activation_format` and :ref:`spike_times_format` dataframes into. 
            Default is 5000.
        client (dask.distributed.Client, optional): 
            Distributed Client object for parallel parsing of anything that isn't a dask dataframe.
        scheduler (dask.distributed.Client, optional)
            Scheduler to use for parallellized parsing of dask dataframes. 
            can e.g. be simply the ``distributed.Client.get`` method.
            Default is None.
        dumper (module, optional):
            Dumper to use for saving pandas dataframes.
            Default is :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.pandas_to_parquet`.
            
    .. deprecated:: 0.2.0
        The :paramref:`burst_times` argument is deprecated and will be removed in a future version.
    '''
    # TODO: many aspects are re-written in optimized format, but can be done in a single pass
    assert dumper.__name__.endswith('.IO.LoaderDumper.pandas_to_msgpack') or dumper.__name__.endswith('.IO.LoaderDumper.pandas_to_parquet'), \
            "Please use a pandas-compatible dumper. You used {}.".format(dumper)
    if dumper.__name__.endswith('pandas_to_msgpack') and six.PY3 and not os.environ.get('ISF_IS_TESTING', False):
        raise DeprecationWarning(
            """The pandas_to_msgpack dumper is deprecated for Python 3.8 and onwards. Use pandas_to_parquet instead.\n
            If you _really_ need to use pandas_to_msgpack for whatever reason, use ISF Py2.7 and pretend to be the test suite by overriding the environment variable ISF_IS_TESTING. 
            See data_base.IO.LoaderDumper.pandas_to_msgpack.dump""")
    if burst_times:
        raise ValueError('deprecated!')
    if rewrite_in_optimized_format:
        assert client is not None
        scheduler = client

    # get = compatibility.multiprocessing_scheduler if get is None else get
    # with dask.set_options(scheduler=scheduler):
    # with get_progress_bar_function()():
    db['simresult_path'] = simresult_path
    
    if core:
        _build_core(db, repartition=repartition, metadata_dumper=dumper)
        if rewrite_in_optimized_format:
            optimize(
                db,
                select=['voltage_traces'],
                repartition=False,
                scheduler=scheduler,
                client=client)
    
    if parameterfiles:
        _build_param_files(db, client=client)
    
    if synapse_activation:
        _build_synapse_activation(
            db,
            repartition=repartition,
            n_chunks=n_chunks)
        if rewrite_in_optimized_format:
            optimize(
                db,
                select=['cell_activation', 'synapse_activation'],
                repartition=False,
                scheduler=scheduler,
                client=client,
                dumper=dumper)
    
    if dendritic_voltage_traces:
        add_dendritic_voltage_traces(
            db, 
            rewrite_in_optimized_format,
            dendritic_spike_times, 
            repartition,
            dendritic_spike_times_threshold, 
            scheduler,
            client, 
            dumper=dumper)
    
    if spike_times:
        # spike times are numbered after this
        logging.info("---spike times---")
        vt = db['voltage_traces']
        db.set(
            'spike_times',
            spike_detection(vt),
            dumper=dumper)
    
    logging.info('Initialization succesful.')


def add_dendritic_voltage_traces(
        db,
        rewrite_in_optimized_format=True,
        dendritic_spike_times=True,
        repartition=True,
        dendritic_spike_times_threshold=-30.,
        scheduler=None,
        client=None,
        dumper=None):
    """Add dendritic voltage traces to the database. 
    
    Used in :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.init` to read, parse
    and write the membrane voltage of recorded sites to the database.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): 
            The database to which the data should be added.
        rewrite_in_optimized_format (bool, optional):
            If True, the data is converted to a high performance format.
            Default is True.
        dendritic_spike_times (bool, optional):
            If True, the dendritic spike times are added to the database.
            Default is True.
        repartition (bool, optional):
            If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
            Default is True.
        dendritic_spike_times_threshold (float, optional):
            Threshold for the dendritic spike times in mV. Default is :math:`-30`.
            See also: :py:meth:`~data_base.isf_data_base.db_initializers.load_simrun_general.add_dendritic_spike_times`
        client (:py:class:`~dask.distributed.client.Client`, optional):
            Distributed Client object for parallel computation.
        dumper (module, optional):
            Dumper to use for :py:meth:`~data_base.isf_data_base.load_simrun_general.optimize` if :paramref:`optimize` is ``True``.
            Default is :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.pandas_to_msgpack`. 
    """
    _build_dendritic_voltage_traces(db, repartition=repartition)
    if rewrite_in_optimized_format:
        optimize(db['dendritic_recordings'],
                 select=list(db['dendritic_recordings'].keys()),
                 repartition=False,
                 scheduler=scheduler,
                 client=client,
                 dumper=dumper)
    if dendritic_spike_times:
        add_dendritic_spike_times(db, dendritic_spike_times_threshold)


def add_dendritic_spike_times(db, dendritic_spike_times_threshold=-30.):
    """Add dendritic spike times to the database.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
            The database to which the data should be added.
        dendritic_spike_times_threshold (float, optional):
            Threshold for the dendritic spike times in mV. Default is :math:`-30`.
            See also: :py:meth:`~data_base.analyze.spike_detection`
    """
    m = db.create_sub_db('dendritic_spike_times')
    for kk in list(db['dendritic_recordings'].keys()):
        vt = db['dendritic_recordings'][kk]
        st = spike_detection(vt, threshold=dendritic_spike_times_threshold)
        m.set(
            kk + '_' + str(dendritic_spike_times_threshold),
            st,
            dumper=OPTIMIZED_PANDAS_DUMPER)


def _get_dumper(value):
    '''Infer the best dumper for a dataframe.
    
    Infers the correct parquet dumper for either a pandas or dask dataframe.
    
    Args:
        value (pd.DataFrame or dd.DataFrame): Dataframe to infer the dumper for.
        
    Returns:
        module: Dumper module to use for the dataframe.
        
    Raises:
        NotImplementedError: If the dataframe is not a pandas or dask dataframe.
    '''
    if six.PY2:
        # For the legacy py2.7 version, it still uses the msgpack dumper
        from data_base.isf_data_base.IO.LoaderDumper import pandas_to_msgpack, dask_to_msgpack
        return pandas_to_msgpack if isinstance(value, pd.DataFrame) else dask_to_msgpack
    elif six.PY3:
        return OPTIMIZED_PANDAS_DUMPER if isinstance(value, pd.DataFrame) else OPTIMIZED_DASK_DUMPER
    else:
        raise NotImplementedError()


def optimize(
    db,
    dumper=None,
    select=None,
    scheduler=None,
    repartition=False,
    client=None):
    '''Rewrite existing data with a new dumper.
    
    It also repartitions dataframes such that they contain 5000 partitions at maximum.
    
    This method is useful to convert older databases that were created with an older 
    (less efficient) dumper.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): 
            The database to optimize.
        dumper (module):
            Dumper to use for re-saving the data in a new format.
            Default is None, and the dumper is inferred from the data type.
            See also: :py:meth:`~data_base.isf_data_base.db_initializers._get_dumper`
        select (list, optional):
            List of keys to optimize. Default is None, and all data is optimized: 
            ``['synapse_activation', 'cell_activation', 'voltage_traces', 'dendritic_recordings']``.
        client (distributed.Client, optional):
            Distributed Client object for parallel computation.

    Returns:
        None
    '''
    keys = list(db.keys())
    keys_for_rewrite = select if select is not None else \
        ['synapse_activation', 'cell_activation', 'voltage_traces', 'dendritic_recordings']
    for key in list(db.keys()):
        if not key in keys_for_rewrite:
            continue
        else:
            value = db[key]
            if isinstance(value, ISFDataBase):
                optimize(
                    value,
                    select=list(value.keys()),
                    scheduler=scheduler,
                    client=client)
            else:
                dumper = _get_dumper(value)
                logging.info(
                    'optimizing {} using dumper {}'.format(
                        str(key), get_dumper_string_by_dumper_module(dumper)
                        ))
                if isinstance(value, dd.DataFrame):
                    db.set(key, value, dumper = dumper, client = client)
                else:
                    # used for *to_msgpack dumpers, but there they seem unused?
                    # also, msgpack is deprecated
                    db.set(key, value, dumper = dumper, scheduler=scheduler)


def load_param_files_from_db(db, sti):
    """Load the :ref:`cell_parameters_format` and :ref:`network_parameters_format` files from the database.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
            The database containing the parsed simulation results.
        sti (str):
            For which simulation trial index to load the parameter files.
            
    Returns:
        tuple: The :py:class:`~sumatra.parameters.NTParameterSet` objects for the cell and network.
    """
    import single_cell_parser as scp
    x = db['parameterfiles'].loc[sti]
    x_neu, x_net = x['hash_neuron'], x['hash_network']
    neuf = db['parameterfiles_cell_folder'].join(x_neu)
    netf = db['parameterfiles_network_folder'].join(x_net)
    return scp.build_parameters(neuf), scp.build_parameters(netf)


def load_initialized_cell_and_evokedNW_from_db(
        db,
        sti,
        allPoints=False,
        reconnect_synapses=True):
    """Load and set up the cell and network from the database.
    
    The cell and network are set up using the parameter files from the database.
    These can then be used to inspect the parameters for each, or to re-run simulations.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
            The database containing the parsed simulation results.
        sti (str):
            For which simulation trial index to load the parameter files.
        allPoints (bool, optional):
            If True, all points of the cell are used. Default is False.
            See also: :py:meth:`single_cell_parser.create_cell`
        reconnect_synapses (bool, optional):
            If True, the synapses are reconnected to the cell. Default is True.
            See also: :py:meth:`single_cell_parser.NetworkMapper.reconnect_saved_synapses`
    
    See also:
        :py:meth:`simrun.rerun_db.rerun_db` for the recommended high-level method
        of re-running simulations from a database.
        
    Returns:
        tuple: The re-initialized :py:class:`single_cell_parser.cell.Cell` and the :py:class:`single_cell_parser.NetworkMapper` objects.
    
    """
    import dask
    from data_base.isf_data_base.IO.roberts_formats import write_pandas_synapse_activation_to_roberts_format
    neup, netp = load_param_files_from_db(db, sti)
    sa = db['synapse_activation']
    sa = sa.loc[sti].compute()
    cell = scp.create_cell(neup.neuron, allPoints=allPoints)
    evokedNW = scp.NetworkMapper(cell, netp.network, simParam=neup.sim)
    if reconnect_synapses:
        with mkdtemp() as folder:
            path = os.path.join(folder, 'synapses.csv')
            write_pandas_synapse_activation_to_roberts_format(path, sa)
            evokedNW.reconnect_saved_synapses(path)
    else:
        evokedNW.create_saved_network2()
    return cell, evokedNW


def convert_df_columns_to_str(df):
    """Convenience method to convert all columns of a dataframe to strings.
    
    :skip-doc:
    """
    df = df.rename(columns={col: '{}'.format(col) for col in df.columns if type(col)!=str})
    return df
