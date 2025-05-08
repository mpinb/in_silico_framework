# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.

"""Utility and convenience functions for the :py:mod:`simrun` package.

Provides functions to parse out specific info from parameter files, silence stdout,
subdivide arrays for multiprocessing purposes, and more.
"""

import inspect
import os
import sys
from collections import defaultdict

import pandas as pd
import six

import single_cell_parser as scp
from data_base.dbopen import resolve_db_path, resolve_reldb_path

defaultdict_defaultdict = lambda: defaultdict(lambda: defaultdict_defaultdict())
from config.isf_logging import logger


def get_cellnumbers_from_confile(confile):
    """Get the amount of cells of each type from a confile.

    :py:meth:`get_cellnumbers_from_confile` reads the confile and returns (alongisde the anatomical ID, here unused) a dictionary of the format::

        {cell_type: [(cellType, cellID, synID), ...]}

    This method fetches the cellID of the last cell each cell type and adds 1 to infer the amount of cells of that type.

    Args:
        confile (str): The path to the :ref:`con_file_format` file.

    Returns:
        dict: A dictionary of the format ``{"cell_type": amount_of_cells}``
    """
    con = scp.reader.read_functional_realization_map(confile)
    con = con[0]
    return {cell_type: con[cell_type][-1][1] + 1 for cell_type in list(con.keys())}


def split_network_param_in_one_elem_dicts(dict_):
    """Split a network parameter dictionary into a list of dictionaries.

    This method is used to split a network parameter dictionary into a list of dictionaries, each containing only one element
    for each key in the original dictionary.

    Args:
        dict_ (dict | :py:class:`~single_cell_parser.parameters.ParameterSet`): The network parameter dictionary.

    Returns:
        list: A list of dictionaries, each containing only one element of the original dictionary.
    """

    out = []
    for k in list(dict_["network"].keys()):
        d = defaultdict_defaultdict()
        d["network"][k] = dict_["network"][k]
        out.append(scp.ParameterSet(d))
    return out


def get_default_arguments(func):
    """Gets the keyword arguments with their default value from any function.

    Args:
        func (callable): The function to get the default arguments from.

    Returns:
        dict: Dictionary where the function names are keys, and their default values are values
    """
    o = inspect.getargspec(func)
    names = o.args[-len(six.get_function_defaults(func)) :]
    defaults = o.defaults
    return {n: d for n, d in zip(names, defaults) if d is not None}


def set_default_arguments_if_not_set(o, kwargs):
    """Set default arguments of an object if they are not set.

    Update attributes of an object based on a dictionary.
    If the attribute is already set, it is NOT opverwritten.
    If an object has been pickled and the keyword arguments have been extended post hoc,
    the new keyword arguments are missing. This can be used to update the object accordingly.

    Args:
        o (object): The object to update.
        kwargs (dict): The dictionary containing the keyword arguments.

    Returns:
        None: Updates the object in place.
    """
    for n, v in six.iteritems(kwargs):
        try:
            getattr(o, n)
        except AttributeError:
            errstr = "Warning! Setting {} to default value {}"
            print(errstr.format(n, v))
            setattr(o, n, v)


def load_param_file_if_path_is_provided(pathOrParam):
    """Convenience function to load a parameter file whether it is a string or a dictionary.

    Args:
        pathOrParam (str | dict | :py:class:`~single_cell_parser.parameters.ParameterSet`): The path to the parameter file or the parameter dictionary.

    Returns:
        :py:class:`~single_cell_parser.parameters.ParameterSet`: The parameter object.
    """
    import single_cell_parser as scp

    if isinstance(pathOrParam, str):
        logger.debug(
            "Reading parameter file from database path: {}".format(pathOrParam)
        )
        pathOrParam = resolve_db_path(pathOrParam)
        return scp.build_parameters(pathOrParam)
    elif isinstance(pathOrParam, dict):
        logger.debug("Building ParameterSet from dictionary")
        return scp.ParameterSet(pathOrParam)
    else:
        logger.warning(
            "Returning parameter object as is (type: {})".format(type(pathOrParam))
        )
        return pathOrParam


class defaultValues:
    """
    :skip-doc:

    TODO: remove this?
    """

    name = "C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center"
    cellParamName = "/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/L5tt/network_embedding/postsynaptic_location/3x3_C2_sampling/C2center/86_CDK_20041214_BAC_run5_soma_Hay2013_C2center_apic_rec.param"
    networkName = "C2_evoked_UpState_INH_PW_1.0_SuW_0.5_active_ex_timing_C2center.param"


def tar_folder(source_dir, delete_folder=True):
    """Compress a folder to ``.tar`` format.

    Args:
        source_dir (str): The path to the folder to compress.
        delete_folder (bool): If ``True``, the original folder will be deleted after compression.

    Returns:
        None: Compresses the folder in place.

    Raises:
        RuntimeError: If the compression command fails
    """
    parent_folder = os.path.dirname(source_dir)
    folder_name = os.path.basename(source_dir)
    source_dir = source_dir.rstrip("/")
    tar_path = source_dir + ".tar.running"
    command = "tar -cf {} -C {} .".format(tar_path, source_dir)
    if os.system(command):
        raise RuntimeError("{} failed!".format(str(command)))
    if delete_folder:
        if os.system("rm -r {}".format(source_dir)):
            raise RuntimeError("deleting folder {} failed!".format(str(source_dir)))
    os.rename(source_dir + ".tar.running", source_dir + ".tar")


def chunkIt(seq, num):
    """Split a sequence in multiple lists which have approximately equal size.

    Args:
        seq (array): The sequence to split.
        num (int): The number of chunks.

    Returns:
        list: A list of lists containing the chunks.

    See also:
        https://stackoverflow.com/questions/2130016/splitting-a-list-of-arbitrary-size-into-only-roughly-n-equal-parts
    """
    avg = len(seq) / float(num)
    out = []
    last = 0.0

    while last < len(seq):
        out.append(seq[int(last) : int(last + avg)])
        last += avg

    return [o for o in out if o]  # filter out empty lists


def silence_stdout(fun):
    """Decorator function to silence a function's output.

    Redirects the standard output to ``os.devnull`` while the function is called,
    and restores the original standard output afterwards.
    To be used as a decorator.

    Args:
        fun (callable): The function to silence.

    Returns:
        callable: The silenced function.
    """

    def silent_fun(*args, **kwargs):
        stdout_bak = sys.stdout
        sys.stdout = open(os.devnull, "w")
        try:
            res = fun(*args, **kwargs)
        except:
            raise
        finally:
            sys.stdout = stdout_bak
        return res

    return silent_fun


def get_fraction_of_landmarkAscii(frac, path):
    """Sample landmarks (i.e. 3D points) from a landmarkAscii file.

    Args:
        frac (float): Fraction of landmarks to sample.
        path (str): The path to the landmarkAscii file.

    Returns:
        pd.DataFrame: A pandas DataFrame containing the sampled landmarks and the cell type.

    See also:
        :py:meth:`~simrun.utils.get_fraction_of_landmarkAscii_dir` to sample landmarks from all landmarkAscii files in a directory.
    """
    f = os.path.basename(path)
    celltype = f.split(".")[-2]
    positions = scp.read_landmark_file(path)
    pdf = pd.DataFrame({"positions": positions, "label": celltype})
    if len(pdf) == 0:  # cannot sample from empty pdf
        return pdf
    if frac >= 1:
        return pdf
    else:
        return pdf.sample(frac=frac)


def get_fraction_of_landmarkAscii_dir(frac, basedir=None):
    """Sample landmarks from all landmarkAscii files in a directory.

    This method loads all landmarkAscii files in a directory and returns a DataFrame containing the sampled landmarks and the cell type.

    Args:
        frac (float): Fraction of landmarks to sample.
        basedir (str): The path to the directory containing the landmarkAscii files.

    Returns:
        pd.DataFrame: A pandas DataFrame containing the sampled landmarks and the cell type.

    See also:
        :py:meth:`~simrun.utils.get_fraction_of_landmarkAscii` to sample landmarks from a single file.
    """
    out = []
    for f in os.listdir(basedir):
        if not f.endswith("landmarkAscii"):
            continue
        out.append(get_fraction_of_landmarkAscii(1, os.path.join(basedir, f)))

    return pd.concat(out).sample(frac=frac).sort_values("label").reset_index(drop=True)


def select_cells_that_spike_in_interval(
    sa, tmin, tmax, set_index=["synapse_ID", "synapse_type"]
):
    """Select cells whose synapses were active in a given time interval.

    Args:
        sa (pd.DataFrame): The :ref:`syn_activation_format` DataFrame.
        tmin (float): The start time of the interval.
        tmax (float): The end time of the interval.
        set_index (list): The index of the DataFrame. Default is ``['synapse_ID', 'synapse_type']``.

    Returns:
        list: A list of tuples containing the synapse ID and the synapse type of the cells that spike in the interval.
    """
    # TODO: bit of a misnomer, no? cell activations and synapse activations are not the same.
    pdf = sa.set_index(list(set_index))
    pdf = pdf[[c for c in pdf.columns if c.isdigit()]]
    pdf = pdf[((pdf >= tmin) & (pdf < tmax)).any(axis=1)]
    cells_that_spike = pdf.index
    cells_that_spike = cells_that_spike.tolist()
    return cells_that_spike

