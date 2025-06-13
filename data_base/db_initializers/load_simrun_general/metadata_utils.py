import glob
import os
import warnings

import dask
import pandas as pd

from data_base.utils import chunkIt


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


@dask.delayed
def create_metadata_parallelization_helper(sim_trial_index, simresult_path):
    """Parallelize creating metadata across multiple simulation trials.

    See also:
        This is used in
        :py:meth:`~data_base.db_initializers.load_simrun_general.create_metadata`.

    Args:
        sim_trial_index (pd.Series): A pandas series containing the sim_trial_index.
        simresult_path (str): Path to the simulation results folder.

    Returns:
        pd.DataFrame: A pandas dataframe containing the metadata.
    """

    def determine_zfill_used_in_simulation(globstring):
        """The number of digits like 0001 or 000001 is not consitent accross
        simulation results. This function takes care of this.

        Args:
            globstring (str): A string containing a glob pattern.

        Returns:
            int: The number of digits used in the simulation results.
        """
        # print globstring
        ret = len(
            os.path.basename(glob.glob(globstring)[0]).split("_")[1].lstrip("run")
        )
        return ret

    def voltage_trace_file_list(x):
        """Returns part of the metadata dataframe.

        This function extracts the path, trial number, and filename of the voltage traces file.

        Args:
            x (pd.Series): A pandas series containing the sim_trial_index.

        Returns:
            pd.Series: A pandas series containing the path, trial number, and filename of the voltage traces file.
        """
        path = x.sim_trial_index
        path, trialnr = os.path.split(path)
        voltage_traces_file_name = os.path.basename(path)
        voltage_traces_file_name = (
            voltage_traces_file_name.split("_")[-1] + "_vm_all_traces.csv"
        )

        return pd.Series(
            {
                "path": path,
                "trialnr": trialnr,
                "voltage_traces_file_name": voltage_traces_file_name,
            }
        )

    def synaptic_file_list(x):
        """Returns part of the metadata dataframe.

        Extracts the filename of the synapse activation file.

        Args:
            x (pd.Series): A pandas series containing the ``trialnr``.

        Returns:
            pd.Series: A pandas series containing the filename of the synapse activation file.
        """
        testpath = os.path.join(
            simresult_path,
            os.path.dirname(list(sim_trial_index.sim_trial_index)[0]),
            "*%s*.csv",
        )
        zfill_synapses = determine_zfill_used_in_simulation(testpath % "synapses")
        synapses_file_name = "simulation_run%s_synapses.csv" % str(
            int(x.trialnr)
        ).zfill(zfill_synapses)
        return pd.Series({"synapses_file_name": synapses_file_name})

    def cells_file_list(x):
        """Returns part of the metadata dataframe.

        Extracts the filename of the cell activation file.

        Args:
            x (pd.Series): A pandas series containing the ``trialnr``.

        Returns:
            pd.Series: A pandas series containing the filename of the cell activation file.
        """
        testpath = os.path.join(
            simresult_path,
            os.path.dirname(list(sim_trial_index.sim_trial_index)[0]),
            "*%s*.csv",
        )
        zfill_cells = determine_zfill_used_in_simulation(testpath % "cells")
        cells_file_name = "simulation_run%s_presynaptic_cells.csv" % str(
            int(x.trialnr)
        ).zfill(zfill_cells)
        return pd.Series({"cells_file_name": cells_file_name})

    path_trialnr = sim_trial_index.apply(voltage_trace_file_list, axis=1)
    sim_trial_index_complete = pd.concat((sim_trial_index, path_trialnr), axis=1)

    try:
        synaptic_files = path_trialnr.apply(synaptic_file_list, axis=1)
        sim_trial_index_complete = pd.concat(
            (sim_trial_index_complete, synaptic_files), axis=1
        )
    except (
        IndexError
    ):  # special case if synapse activation data is not in the simulation folder
        warnings.warn("Could not find synapse activation files")
    try:
        cell_files = path_trialnr.apply(cells_file_list, axis=1)
        sim_trial_index_complete = pd.concat(
            (sim_trial_index_complete, cell_files), axis=1
        )
    except IndexError:
        warnings.warn("could not find cell activation files")
    return sim_trial_index_complete


def create_metadata(db):
    """Generate metadata out of a pd.Series containing the sim_trial_index.

    Expands the sim_trial_index to a pandas Series containing the path, trial number,
    and filename of the voltage traces file. After running this method, the database
    contains:

    - ``sim_trial_index`` A pandas series containing the sim_trial_index.
    - ``simresult_path`` Path to the simulation results folder.

    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`):
            The target database that should contain the parsed simulation results.

    Returns:
        pd.DataFrame: A pandas dataframe containing the metadata.
    """
    simresult_path = db["simresult_path"]
    sim_trial_index = list(db["sim_trial_index"])
    sim_trial_index = pd.DataFrame(dict(sim_trial_index=list(sim_trial_index)))
    sim_trial_index_delayed = dask.dataframe.from_pandas(sim_trial_index, npartitions=5000).to_delayed()
    sim_trial_index_complete = [
        create_metadata_parallelization_helper(d, simresult_path)
        for d in sim_trial_index_delayed
    ]
    sim_trial_index_complete = dask.compute(sim_trial_index_complete)
    sim_trial_index_complete = pd.concat(sim_trial_index_complete[0])
    return sim_trial_index_complete
