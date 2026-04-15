"""Parse :ref:`simresult_dir_format` generated with :mod:`simrun` and write to a :class:`data_base.DataBase`

The output format of :mod:`simrun` are :ref:`simresult_dir_format`: a nested folder structure with ``.csv`` and/or ``.npz`` files.
This module provides functions to gather and parse this data to pandas and dask dataframes. It merges all trials in a single dataframe.
This saves IO time, disk space, and is strongly recommended for HPC systems and other shared filesystems in general, as it reduces the amount of inodes required. 

After running :func:`~data_base.db_initializers.load_simrun_general.init`, a database is created containing
the following keys:

.. list-table::
    :header-rows: 1

    * - Key
      - Description
    * - ``simresult_path``
      - Filepath to the raw simulation output of :mod:`simrun`
    * - ``filelist``
      - List containing paths to all original somatic voltage trace files.
    * - ``sim_trial_index``
      - The simulation trial indices as a pandas Series.
    * - ``metadata``
      - A metadata dataframe out of sim_trial_indices
    * - ``voltage_traces``
      - Dask dataframe containing the somatic voltage traces
    * - ``parameterfiles_cell_folder``
      - A :class:`~data_base.isf_data_base.IO.LoaderDumper.just_create_folder.ManagedFolder` 
        containing the :ref:`cell_parameters_format` file, renamed to its file hash.
    * - ``parameterfiles_network_folder``
      - A :class:`~data_base.isf_data_base.IO.LoaderDumper.just_create_folder.ManagedFolder`
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

      
If you intialize the database with ``rewrite_in_optimized_format=True`` (default), the keys are written as dask dataframes to whichever format is configured as the optimized format (see :py:mod:`~data_base.isf_data_base.db_initializers.load_simrun_general.config`).
If ``rewrite_in_optimized_format=False`` instead, these keys are pickled dask dataframes, containing the instructions to build the dataframe, not the data itself.
This is useful for fast intermediate analysis, but strongly discouraged for long term storage, since these instructions contain absolute paths to the original data files, which invalidates once they are moved or deleted.
Individual keys can afterwards be set to permanent, self-contained and efficient dask dataframes by calling 
:py:meth:`~data_base.db_initializers.load_simrun_general.load_simrun_general.optimize` on specific database
keys.

Example::

    >>> paramfile_copy_config = {
    ...     "copy_method": "remount",
    ...     "neup" : "parameterfiles_folder",
    ...     "netp" : "parameterfiles_folder",
    ...     "morph" : "morphology_folder",
    ...     "syn" : "parameterfiles_folder",
    ...     "con" : "parameterfiles_folder",
    ...     "recsites" : "parameterfiles_folder"
    ... }
    >>> simresult_path = '/path/to/raw/simrun/output/folder'
    >>> db = I.DataBase("db_parsed_data")
    >>> client = distributed.Client("localhost:8786")
    >>> I.db_init_simrun_general.init(
    ... db = db,
    ... simresult_path = p,
    ... core = True, 
    ... repartition = 500,
    ... parameterfiles = True,
    ... synapse_activation = True, 
    ... n_chunks = 5000,
    ... dendritic_voltage_traces = True,
    ... spike_times = True, 
    ... dendritic_spike_times = False,
    ... rewrite_in_optimized_format = True,
    ... client = client,
    ... check_health = True,
    ... paramfile_copy_config = paramfile_copy_config
    ... )

After initialization, you can access the data from the data_base in the following manner::

    >>> db['synapse_activation']
    <synapse activation dataframe>
    >>> db['cell_activation']
    <cell activation dataframe>
    >>> db['voltage_traces']
    <voltage traces dataframe>
    >>> db['spike_times']
    <spike times dataframe>
    
If you intialize the database with ``rewrite_in_optimized_format=True`` (default), the keys are written as dask dataframes to whichever format is configured as the optimized format (see :mod:`~data_base.isf_data_base.db_initializers.load_simrun_general.config`).
If ``rewrite_in_optimized_format=False`` instead, these keys are pickled dask dataframes, containing the instructions to build the dataframe, not the data itself.
This is useful for fast intermediate analysis, but strongly discouraged for long term storage, since these instructions contain absolute paths to the original data files, which invalidates once they are moved or deleted.
Individual keys can afterwards be set to permanent, self-contained and efficient dask dataframes by calling 
:func:`~data_base.db_initializers.load_simrun_general.load_simrun_general.optimize` on specific database
keys.

See also:
    :ref:`simresult_dir_format` for more information on the raw output format of :mod:`simrun`.

See also:
    :func:`~data_base.db_initializers.load_simrun_general.init` for the initialization of the database.
"""

import logging
import os

import dask.dataframe as dd

import single_cell_parser as scp
from data_base.analyze.spike_detection import spike_detection
from data_base import is_data_base
from data_base.IO.LoaderDumper import get_dumper_string_by_dumper_module
from data_base.utils import mkdtemp
from .config import OPTIMIZED_PANDAS_DUMPER

from .builders import (
    _build_core,
    _build_dendritic_voltage_traces,
    _build_param_files,
    _build_synapse_activation,
)
from .data_parsing import (
    load_dendritic_voltage_traces,
    read_voltage_traces_from_file
)
from .param_file_parser import load_param_files_from_db
from .utils import _get_dumper
from .reoptimize import reoptimize_db

logger = logging.getLogger("ISF").getChild(__name__)

DEFAULT_PARAMFILE_COPY_CONFIG = {
    "copy_method": "remount",
    "neup" : "parameterfiles_folder",
    "netp" : "parameterfiles_folder",
    "morph" : "parameterfiles_folder",
    "syn" : "parameterfiles_folder",
    "con" : "parameterfiles_folder",
    "recsites" : "parameterfiles_folder"
}

def init(
    db,
    simresult_path,
    core=True,
    synapse_activation=True,
    dendritic_voltage_traces=True,
    parameterfiles=True,
    spike_times=True,
    repartition=True,
    scheduler=None,
    rewrite_in_optimized_format=True,
    dendritic_spike_times=True,
    dendritic_spike_times_threshold=-30.0,
    client=None,
    check_health=False,
    n_chunks=5000,
    paramfile_copy_config=None,
    # deprecated args;
    voltage_traces=None,
    burst_times=None,
    dumper=None,
):
    """Initialize a database with simulation data.

    Use this function to load simulation data generated with the simrun module
    into a :class:`~data_base.DataBase`. 

    Most configuration options you would want to change on a init-by-init basis are given here as keyword arguments.
    Additional options can be configured in :mod:`data_base.db_initializers.load_simrun_general.config`

    Args:
        db (:class:`~data_base.DataBase`):
            The database to store the simulation results in.
        core (bool, optional):
            Parse and write the core data to the database: voltage traces, metadata, sim_trial_index and filelist.
        spike_times (bool, optional):
            Parse and write the spike times into the database.
            See also: :func:`data_base.analyze.spike_detection.spike_detection`
        dendritic_voltage_traces (bool, optional):
            Parse and write the dendritic voltage traces to the database.
        dendritic_spike_times (bool, optional):
            Parse and write the dendritic spike times to the database.
        dendritic_spike_times_threshold (float, optional):
            Threshold for the dendritic spike times in :math:`mV`. Default is :math:`-30 mV`.
        synapse_activation (bool, optional):
            Parse and write the synapse activation data to the database.
        parameterfiles (bool, optional):
            Resolve and copy the parameterfiles used in each simulation to the database.
            Since this copies all parameterfiels required to rerun simulations, this makes the database self-containing and portable.
            You could then remove the original raw simulation data, provided you have selected all desired results in the keyword arguments here.
        rewrite_in_optimized_format (bool, optional):
            If True (default): data is converted to a high performance binary format
            If False: the db only contains links (pickled objects) to the actual simulation data folder
            and will not work if the data folder is deleted or moved or transferred to another machine.
        repartition (bool|int): 
            If ``int``, the voltage trace dataframes will be partitioned to be of this length (approximately).
            If ``True``, the voltage trace dataframes will be partitioned to be of a default length: :attr:`~data_base.db_initializers.load_simrun_general.data_parsing.DEFAULT_VT_PARTITION_SIZE`
            If ``False``, the voltage trace dataframe will not be repartitioned, and the dask dataframe will be one ``.csv`` file per partition.
        n_chunks (int, optional):
            Amount of partitions to split the :ref:`syn_activation_format` and :ref:`spike_times_format` dataframes into.
            Default is :math:`5000`.
        paramfile_copy_config (dict, optional): 
            Dictionary containing configuration on how to organise parameterfiles in the database. Options are:
    
            - ``copy_method`` (str): Which copy strategy to use. 
              Must be either ``"hash_rename"`` or ``"remount"``. 
              ``"hash_rename"`` will rename all parameterfiles to a hash of their content. Useful when you want all parameter files in one folder and avoid fielname clashes.
              ``"remount"`` will preserve the relative directory structure of the parameterfiles per file category (see below). Useful when parameterfiles are already organized.
            - "neup" (str): Target directory name of :ref:`cell_parameters_format`. Default is ``"parameterfiles_folder"``
            - "netp" (str): Target directory name of :ref:`network_parameters_format`. Default is ``"parameterfiles_folder"``
            - "morph" (str): Target directory name of :ref:`morphology_file_format` files. Default is ``"parameterfiles_folder"``
            - "syn" (str): Target directory name of :ref:`syn_file_format` files. Default is ``"parameterfiles_folder"``
            - "con" (str): Target directory name of :ref:`con_file_format` files. Default is ``"parameterfiles_folder"``
            - "recsites" (str): Target directory name of recordingsites (``.landmarkAscii``). Default is ``"parameterfiles_folder"``

        client (:class:`distributed.Client`, optional):
            Distributed Client object for parallel parsing of anything that isn't a dask dataframe.
        scheduler (:class:`distributed.Client`, optional)
            Scheduler to use for parallellized parsing of dask dataframes.
            can e.g. be simply the ``distributed.Client.get`` method.
            Default is ``None``.

            
    Note:
        Note the difference between *amount* of partitions (:param:`n_chunks`) and target partition *size* (:param:`repartition`)

    .. deprecated:: 0.2.0
        The :paramref:`burst_times` argument is deprecated and will be removed in a future version.
        
    .. versionadded:: 0.5.0
       The keyword argument :param:`repartition` now accepts integers in addition to booleans.
       Integers reflect the target size of each voltage trace dataframe partition. Booleans reflect either
       ``True`` for a default lenght, or ``False`` for no repartitioning (i.e. one ``.csv`` file per partition)

    .. deprecated:: 0.2.0
        The :param:`burst_times` argument is deprecated and will be removed in a future version.
        
    .. deprecated:: 0.5.0
       The :param:`dumper` argument is deprecated and will be removed in a future version.
       Dumpers are configured in the centralized :mod:`~data_base.db_initializers.load_simrun_general.config` module.
    
    .. deprecated:: 0.5.0
       The :param:`voltage_traces` is deprecated and will be removed in a future version.
       Voltage traces are always built when :param:`core` is ``True``. 

    """
    if burst_times is not None:
        logger.warning("The burst_times argument is deprecated and will be removed in a future version. Ignoring and continuing...")
    if voltage_traces is not None:
        logger.warning("The voltage_trace argument is deprecated and will be removed in a future version. Voltage traces are always built when core=True, and don't need a duplicate kwarg. Ignoring and continuing...")
    if dumper is not None:
        logger.warning("The dumper argument is deprecated and will be removed in a future version. Dumpers for specific keys are configured in the data_base.db_initializers.load_simrun_general.config. Ignoring and continuing...")
    if rewrite_in_optimized_format:
        assert client is not None
        scheduler = client

    # Update unspecified paramfile config settings to default
    paramfile_copy_config = paramfile_copy_config or {}
    assert all([k in DEFAULT_PARAMFILE_COPY_CONFIG for k in paramfile_copy_config]), "Please pass a recognized config option for parameterfiles: {}".format(DEFAULT_PARAMFILE_COPY_CONFIG.keys())
    if "copy_method" in paramfile_copy_config:
        assert paramfile_copy_config['copy_method'] in ("hash_rename", "remount"), "Please provide a recognized copy method option: hash_rename or remount"
    for k, v in DEFAULT_PARAMFILE_COPY_CONFIG.items(): 
        paramfile_copy_config.setdefault(k, v)

    # get = compatibility.multiprocessing_scheduler if get is None else get
    # with dask.set_options(scheduler=scheduler):
    # with get_progress_bar_function()():
    db["simresult_path"] = simresult_path

    if core:
        _build_core(
            db, 
            repartition=repartition, 
            metadata_dumper=OPTIMIZED_PANDAS_DUMPER,
            client=client,
            check_health=check_health,
            )
        if rewrite_in_optimized_format:
            optimize(
                db,
                select=["voltage_traces"],
                repartition=False,
                scheduler=scheduler,
                client=client,
            )

    if parameterfiles:
        _build_param_files(db, paramfile_copy_config=paramfile_copy_config, client=client)

    if synapse_activation:
        _build_synapse_activation(db, repartition=repartition, n_chunks=n_chunks)
        if rewrite_in_optimized_format:
            optimize(
                db,
                select=["cell_activation", "synapse_activation"],
                repartition=False,
                scheduler=scheduler,
                client=client,
                categorized=True,
            )

    if dendritic_voltage_traces:
        add_dendritic_voltage_traces(
            db,
            rewrite_in_optimized_format,
            dendritic_spike_times,
            repartition,
            dendritic_spike_times_threshold,
            scheduler,
            client,
        )

    if spike_times:
        # spike times are numbered after this
        logging.info("---spike times---")
        vt = db["voltage_traces"]
        db.set("spike_times", spike_detection(vt))

    logging.info("Initialization succesful.")


def add_dendritic_voltage_traces(
    db,
    rewrite_in_optimized_format=True,
    dendritic_spike_times=True,
    repartition=True,
    dendritic_spike_times_threshold=-30.0,
    scheduler=None,
    client=None,
):
    """Add dendritic voltage traces to the database.

    Used in :func:`~data_base.db_initializers.load_simrun_general.init` to read, parse
    and write the membrane voltage of recorded sites to the database.

    Args:
        db (:class:`~data_base.DataBase`):
            The database to which the data should be added.
        rewrite_in_optimized_format (bool, optional):
            If True, the data is converted to a high performance format.
            Default is ``True``.
        dendritic_spike_times (bool, optional):
            If True, the dendritic spike times are added to the database.
            Default is ``True``.
        repartition (bool, optional):
            If True, the dask dataframe is repartitioned to 5000 partitions (only if it contains over :math:`10000` entries).
            Default is ``True``.
        dendritic_spike_times_threshold (float, optional):
            Threshold for the dendritic spike times in :math:`mV`. Default is :math:`-30 mV`.
            See also: :func:`~data_base.db_initializers.load_simrun_general.add_dendritic_spike_times`
        client (:class:`~dask.distributed.client.Client`, optional):
            Distributed Client object for parallel computation.
    """
    # Set a pickle to the dend voltage traces. This is simply a symlink to the original data, not the data itself.
    _build_dendritic_voltage_traces(db, repartition=repartition)
    
    if rewrite_in_optimized_format:
        subselection = list(db["dendritic_recordings"].keys())
        # Actually load and parse the data to a format: this is not a symlink anymore
        optimize(
            db["dendritic_recordings"],
            select=subselection,       
            repartition=False,
            scheduler=scheduler,
            client=client,
        )
    if dendritic_spike_times:
        add_dendritic_spike_times(db, dendritic_spike_times_threshold)


def add_dendritic_spike_times(db, dendritic_spike_times_threshold=-30.0):
    """Add dendritic spike times to the database.

    Args:
        db (:class:`~data_base.DataBase`):
            The database to which the data should be added.
        dendritic_spike_times_threshold (float, optional):
            Threshold for the dendritic spike times in :math:`mV`. Default is :math:`-30 mV`.
            See also: :func:`~data_base.analyze.spike_detection`
    """
    m = db.create_sub_db("dendritic_spike_times")
    for kk in list(db["dendritic_recordings"].keys()):
        vt = db["dendritic_recordings"][kk]
        st = spike_detection(vt, threshold=dendritic_spike_times_threshold)
        m.set(
            kk + "_" + str(dendritic_spike_times_threshold),
            st,
            dumper=None,
        )


def optimize(
    db, 
    dumper=None, 
    select=None, 
    scheduler=None, 
    repartition=False, 
    categorized=False, 
    client=None
):
    """Rewrite existing data with a new dumper.

    It also repartitions dataframes such that they contain 5000 partitions at maximum.

    This method is useful to convert older databases that were created with an older
    (less efficient) dumper.

    Args:
        db (:class:`~data_base.DataBase`):
            The database to optimize.
        select (list, optional):
            List of keys to optimize. Default is ``None``, and all data is optimized:
            ``['synapse_activation', 'cell_activation', 'voltage_traces', 'dendritic_recordings']``.
        client (distributed.Client, optional):
            Distributed Client object for parallel computation.
        dumper (module, deprecated):
            Dumper to use for re-saving the data in a new format.
            Default is ``None``, and the dumper is inferred from the data type.
            See also: :func:`~data_base.db_initializers._get_dumper`
            
    .. deprecated:: 0.5.0
        The :param:`dumper` argument is deprecated and will be removed in a future version.
        Dumpers are configured in the centralized :mod:`~data_base.db_initializers.load_simrun_general.config` module.

    Returns:
        None
    """
    keys = list(db.keys())
    keys_for_rewrite = (
        select
        if select is not None
        else [
            "synapse_activation",
            "cell_activation",
            "voltage_traces",
            "dendritic_recordings",
        ]
    )
    for key in list(db.keys()):
        if not key in keys_for_rewrite:
            continue
        else:
            value = db[key]
            if is_data_base(db._convert_key_to_path(key)):
                optimize(
                    value, select=list(value.keys()), scheduler=scheduler, client=client
                )
            else:
                dumper = _get_dumper(value, categorized=categorized)
                logging.info(
                    "Optimizing {} using dumper {}".format(
                        str(key), get_dumper_string_by_dumper_module(dumper)
                    )
                )
                if isinstance(value, dd.DataFrame):
                    db.set(key, value, dumper=dumper, client=client)
                else:
                    # used for *to_msgpack dumpers, but there they seem unused?
                    # also, msgpack is deprecated
                    db.set(key, value, dumper=dumper, scheduler=scheduler)


def load_initialized_cell_and_evokedNW_from_db(
    db, sti, allPoints=False, reconnect_synapses=True
):
    """Load and set up the cell and network from the database.

    The cell and network are set up using the parameter files from the database.
    These can then be used to inspect the parameters for each, or to re-run simulations.

    Args:
        db (:class:`~data_base.DataBase`):
            The database containing the parsed simulation results.
        sti (str):
            For which simulation trial index to load the parameter files.
        allPoints (bool, optional):
            If True, all points of the cell are used. Default is ``False``.
            See also: :func:`single_cell_parser.create_cell`
        reconnect_synapses (bool, optional):
            If True, the synapses are reconnected to the cell. Default is ``True``.
            See also: :func:`single_cell_parser.NetworkMapper.reconnect_saved_synapses`

    See also:
        :func:`simrun.rerun_db.rerun_db` for the recommended high-level method
        of re-running simulations from a database.

    Returns:
        tuple: The re-initialized :class:`single_cell_parser.cell.Cell` and the :class:`single_cell_parser.NetworkMapper` objects.

    """
    from data_base.IO.roberts_formats import (
        write_pandas_synapse_activation_to_roberts_format,
    )

    neup, netp = load_param_files_from_db(db, sti)
    sa = db["synapse_activation"]
    sa = sa.loc[sti].compute()
    cell = scp.create_cell(neup.neuron, allPoints=allPoints)
    evokedNW = scp.NetworkMapper(cell, netp.network, simParam=neup.sim)
    if reconnect_synapses:
        with mkdtemp() as folder:
            path = os.path.join(folder, "synapses.csv")
            write_pandas_synapse_activation_to_roberts_format(path, sa)
            evokedNW.reconnect_saved_synapses(path)
    else:
        evokedNW.create_saved_network2()
    return cell, evokedNW
