import fnmatch, logging, os, re, dask

from os import walk

from data_base.IO.roberts_formats import _max_commas
from data_base.utils import chunkIt

logger = logging.getLogger("ISF").getChild(__name__)

def make_filelist(directory, suffix="vm_all_traces.csv"):
    """Generate a list of all files with :param:`suffix` in the specified directory.

    This method recursively searches through the directory and its subdirectories
    for files that match the specified suffix. It returns a list of relative paths to
    these files, excluding any files that are still being written to (identified by
    the presence of "_running" in the filename).

    Simulation results from :mod:`simrun` are stored in a nested folder structure, and spread
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
    for root, _, filenames in walk(directory):
        for filename in fnmatch.filter(filenames, "*" + suffix):
            dummy = os.path.join(root, filename)
            if "_running" in dummy:
                logger.warning("Skipping incomplete simulation: {}".format(dummy))
            else:
                matches.append(os.path.relpath(dummy, directory))

    if len(matches) == 0:
        raise ValueError(
            "Did not find any '*{suffix}'-files. Filelist empty. Abort initialization.".format(
                suffix=suffix
            )
        )
    return matches


def get_file(self, suffix):
    """Get the filename of the unique file in the current directory with the specified suffix.

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
            "The folder {} does not contain a file with the suffix {}".format(
                self, suffix
            )
        )
    elif len(l) > 1:
        raise ValueError(
            "The folder {} contains several files with the suffix {}".format(
                self, suffix
            )
        )
    else:
        return os.path.join(self, l[0])


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
        """determine maximum number of delimiters (\t or ,) in files
        specified by list of filepaths"""
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


def get_recsite_labels_from_dend_vt_filelist(filelist, full_suffix):
    """Get the recording site labels from a list of dendritic voltage trace files.
    
    Example:
        >>> fn = "path/to/YYYYMMDD-HHMM_seed001_pid001/seed001_pid001_pos_1_ID_000_sec_073_seg_000_x_0.056_somaDist_581.6_vm_dend_traces.csv"
        >>> suffix = "_vm_dend_traces.csv"  # needs leading underscore and .csv extension
        >>> get_recsite_labels_from_dend_vt_filelist([fn], full_suffix=suffix)
        ["pos_1_ID_000_sec_073_seg_000_x_0.056_somaDist_581.6"]

    Args:
        filelist (List[str]): List of filenames to dendritic voltage trace results.
        full_suffix (str): 
            Shared suffix of the filenames that is mutually exclusive from the recsite label. 
            This is normally fetched by the higher-level :func:`load_dendritic_voltage_traces`

    Returns:
        List[str]: List of recording site labels.
    """
    # simresult_dirs, fns = zip(*[
    #     (
    #         os.path.basename(os.path.dirname(e)), 
    #         os.path.basename(e)
    #     ) 
    #     for e in filelist])
    #    old naming convention: subdirectory/20250101-1553_0001/*
    #  newer naming convention: subdirectory/20250101-1553_seed0001/*
    # newest naming convention: subdirectoy/20250101-1553_seed123456_pid0001/*
    # prefixes_no_date = ["_".join(e.split("_")[1:]) for e in simresult_dirs]
    
    # example file:
    # seed2622647967_pid162918_pos_1_ID_000_sec_073_seg_000_x_0.056_somaDist_581.6_vm_dend_traces.csv
    # ------- prefix -------- _----------------- recsite label ------------------ _------ suffix ----
    # recsite_labels = [
    #         e[len(prefix)+1:-len(full_suffix)-1] 
    #         for e, prefix in zip(fns, prefixes_no_date)
    #         ]

    basenames = [os.path.basename(e) for e in filelist]
    pattern = re.compile(r"(seed\d+)?_?(pid\d+)?_?(?P<recsite_label>[a-zA-Z0-9\._]+)(?=_).*" + re.escape(full_suffix))
    recsite_labels = [re.match(pattern, e).group("recsite_label") for e in basenames]
    return recsite_labels

    
def _get_recsite_ids_from_recsite_labels(recsite_labels):
    """Fetch the recsite ID number from the entrie recsite ID string.
    
    This function assumes all recsite ids in :param:`recsite_ids` have a substring containing "ID_[digit]",
    where digit is any numeric combination.

    Args:
        recsite_labels (List[str]): List of recording site labels.
    
    Example:
        >>> recsite_label = "pos_54_ID_000_sec_073_seg_003_x_0.318_somaDist_759.1"
        >>> _get_recsite_id_from_labels([recsite_label, recsite_label])
        ["000", "000"]

    Returns:
        List[str]: List of recsite IDs in the same order as the input recsite labels
    """
    pattern = re.compile(r"ID_(?P<number>\d+)")
    try:
        ids = [pattern.search(e).group("number") for e in recsite_labels]
    except AttributeError as e:
        raise ValueError("Found recsite IDs that don't contain the substring ID_[digits]: {}".format(recsite_labels)) from e
    return ids
