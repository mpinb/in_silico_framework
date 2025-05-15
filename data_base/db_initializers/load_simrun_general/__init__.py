"""Parse simulation data generated with :py:mod:`simrun` for general purposes.

The output format of :py:mod:`simrun` is a nested folder structure with ``.csv`` and/or ``.npz`` files.
The voltage traces are written to a single ``.csv`` file (since the amount of timesteps is known in advance, at least for non-variable timesteps),
but the synapse and cell activation data is written to a separate file for each simulation trial (the amount 
of spikes and synapse activations is not known in advance).

This module provides functions to gather and parse this data to pandas and dask dataframes. It merges all trials in a single dataframe.
This saves IO time, disk space, and is strongly recommended for HPC systems and other shared filesystems in general, as it reduces the amount of inodes required. 

After running :py:meth:`~data_base.db_initializers.load_simrun_general.init`, a database is created containing
the following keys:

.. list-table::
    :header-rows: 1

    * - Key
      - Description
    * - ``simresult_path``
      - Filepath to the raw simulation output of :py:mod:`simrun`
    * - ``filelist``
      - List containing paths to all original somatic voltage trace files.
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
    
If you intialize the database with ``rewrite_in_optimized_format=True`` (default), the keys are written as dask dataframes to whichever format is configured as the optimized format (see :py:mod:`~data_base.isf_data_base.db_initializers.load_simrun_general.config`).
If ``rewrite_in_optimized_format=False`` instead, these keys are pickled dask dataframes, containing relative links to the
original ``.csv`` files. In essence, the dask dataframes contain the insturctions to build the dataframe, not the data itself.
This is useful for fast intermediate analysis. It is not intended and strongly discouraged for long term storage. 
Individual keys can afterwards be set to permanent, self-contained and efficient dask dataframes by calling 
:py:meth:`~data_base.db_initializers.load_simrun_general.load_simrun_general.optimize` on specific database
keys.

Attention:
    Note that the database contains symlinks to the original simulation files. This is useful for fast intermediate analysis, but
    for long-term storage, it happens that the original files are deleted, moved, or archived in favor of the optimized format. 
    In this case, the symlinks will point to non-existent files.

See also:
    :py:meth:`simrun.run_new_simulations._evoked_activity` for more information on the raw output format of :py:mod:`simrun`.
    :py:meth:`~data_base.db_initializers.load_simrun_general.init` for the initialization of the database.
"""

import logging
import os

import dask.dataframe as dd

import single_cell_parser as scp
from data_base.analyze.spike_detection import spike_detection
from data_base.data_base import is_data_base
from data_base.IO.LoaderDumper import get_dumper_string_by_dumper_module
from data_base.utils import mkdtemp
from .config import OPTIMIZED_PANDAS_DUMPER

logger = logging.getLogger("ISF").getChild(__name__)


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


def init(
    db,
    simresult_path,
    core=True,
    voltage_traces=True,
    synapse_activation=True,
    dendritic_voltage_traces=True,
    parameterfiles=True,
    spike_times=True,
    burst_times=False,
    repartition=True,
    scheduler=None,
    rewrite_in_optimized_format=True,
    dendritic_spike_times=True,
    dendritic_spike_times_threshold=-30.0,
    client=None,
    n_chunks=5000,
    dumper=None,
):
    """Initialize a database with simulation data.

    Use this function to load simulation data generated with the simrun module
    into a :py:class:`~data_base.DataBase`.

    Args:
        core (bool, optional):
            Parse and write the core data to the database: voltage traces, metadata, sim_trial_index and filelist.
            See also: :py:meth:`~data_base.db_initializers.load_simrun_general._build_core`
        voltage_traces (bool, optional):
            Parse and write the somatic voltage traces to the database.
        spike_times (bool, optional):
            Parse and write the spike times into the database.
            See also: :py:meth:`data_base.analyze.spike_detection.spike_detection`
        dendritic_voltage_traces (bool, optional):
            Parse and write the dendritic voltage traces to the database.
            See also: :py:meth:`~data_base.db_initializers.load_simrun_general._build_dendritic_voltage_traces`
        dendritic_spike_times (bool, optional):
            Parse and write the dendritic spike times to the database.
            See also: :py:meth:`~data_base.db_initializers.load_simrun_general.add_dendritic_spike_times`
        dendritic_spike_times_threshold (float, optional):
            Threshold for the dendritic spike times in :math:`mV`. Default is :math:`-30 mV`.
            See also: :py:meth:`~data_base.db_initializers.load_simrun_general.add_dendritic_spike_times`
        synapse_activation (bool, optional):
            Parse and write the synapse activation data to the database.
            See also: :py:meth:`~data_base.db_initializers.load_simrun_general._build_synapse_activation`
        parameterfiles (bool, optional):
            Parse and write the parameterfiles to the database.
            See also: :py:meth:`~data_base.db_initializers.load_simrun_general._build_param_files`
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
            Default is ``None``.
        dumper (module, optional, deprecated):
            Dumper to use for saving pandas dataframes.
            Default is :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.pandas_to_msgpack`.
            This has been deprecated in favor of a central configuration for the dumpers.

    .. deprecated:: 0.2.0
        The :paramref:`burst_times` argument is deprecated and will be removed in a future version.
        
    .. deprecated:: 0.5.0
       The :paramref:`dumper` argument is deprecated and will be removed in a future version.
       Dumpers are configured in the centralized :py:mod:`~data_base.db_initializers.load_simrun_general.config` module.
    """
    if burst_times:
        raise ValueError("deprecated!")
    if rewrite_in_optimized_format:
        assert client is not None
        scheduler = client

    # get = compatibility.multiprocessing_scheduler if get is None else get
    # with dask.set_options(scheduler=scheduler):
    # with get_progress_bar_function()():
    db["simresult_path"] = simresult_path

    if core:
        _build_core(db, repartition=repartition, metadata_dumper=OPTIMIZED_PANDAS_DUMPER)
        if rewrite_in_optimized_format:
            optimize(
                db,
                select=["voltage_traces"],
                repartition=False,
                scheduler=scheduler,
                client=client,
            )

    if parameterfiles:
        _build_param_files(db, client=client)

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

    Used in :py:meth:`~data_base.db_initializers.load_simrun_general.init` to read, parse
    and write the membrane voltage of recorded sites to the database.

    Args:
        db (:py:class:`~data_base.DataBase`):
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
            See also: :py:meth:`~data_base.db_initializers.load_simrun_general.add_dendritic_spike_times`
        client (:py:class:`~dask.distributed.client.Client`, optional):
            Distributed Client object for parallel computation.
    """
    # Set a pickle to the dend voltage traces. This is simply a symlink to the original data, not the data itself.
    _build_dendritic_voltage_traces(db, repartition=repartition)
    
    if rewrite_in_optimized_format:
        # Actually load and parse the data to a format: this is not a symlink anymore
        optimize(
            db["dendritic_recordings"],
            select=list(db["dendritic_recordings"].keys()),
            repartition=False,
            scheduler=scheduler,
            client=client,
        )
    if dendritic_spike_times:
        add_dendritic_spike_times(db, dendritic_spike_times_threshold)


def add_dendritic_spike_times(db, dendritic_spike_times_threshold=-30.0):
    """Add dendritic spike times to the database.

    Args:
        db (:py:class:`~data_base.DataBase`):
            The database to which the data should be added.
        dendritic_spike_times_threshold (float, optional):
            Threshold for the dendritic spike times in :math:`mV`. Default is :math:`-30 mV`.
            See also: :py:meth:`~data_base.analyze.spike_detection`
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
    db, dumper=None, select=None, scheduler=None, repartition=False, categorized=False, client=None
):
    """Rewrite existing data with a new dumper.

    It also repartitions dataframes such that they contain 5000 partitions at maximum.

    This method is useful to convert older databases that were created with an older
    (less efficient) dumper.

    Args:
        db (:py:class:`~data_base.DataBase`):
            The database to optimize.
        select (list, optional):
            List of keys to optimize. Default is ``None``, and all data is optimized:
            ``['synapse_activation', 'cell_activation', 'voltage_traces', 'dendritic_recordings']``.
        client (distributed.Client, optional):
            Distributed Client object for parallel computation.
        dumper (module, deprecated):
            Dumper to use for re-saving the data in a new format.
            Default is ``None``, and the dumper is inferred from the data type.
            See also: :py:meth:`~data_base.db_initializers._get_dumper`
            
    .. deprecated:: 0.5.0
        The :paramref:`dumper` argument is deprecated and will be removed in a future version.
        Dumpers are configured in the centralized :py:mod:`~data_base.db_initializers.load_simrun_general.config` module.

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
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
            The database containing the parsed simulation results.
        sti (str):
            For which simulation trial index to load the parameter files.
        allPoints (bool, optional):
            If True, all points of the cell are used. Default is ``False``.
            See also: :py:meth:`single_cell_parser.create_cell`
        reconnect_synapses (bool, optional):
            If True, the synapses are reconnected to the cell. Default is ``True``.
            See also: :py:meth:`single_cell_parser.NetworkMapper.reconnect_saved_synapses`

    See also:
        :py:meth:`simrun.rerun_db.rerun_db` for the recommended high-level method
        of re-running simulations from a database.

    Returns:
        tuple: The re-initialized :py:class:`single_cell_parser.cell.Cell` and the :py:class:`single_cell_parser.NetworkMapper` objects.

    """
    from data_base.isf_data_base.IO.roberts_formats import (
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
