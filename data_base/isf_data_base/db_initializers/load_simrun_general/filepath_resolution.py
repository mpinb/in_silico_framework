from data_base.dbopen import (
    create_modular_db_path,
    create_reldb_path,
    resolve_reldb_path,
)
import re
from data_base.exceptions import DataBaseException
import logging

logger = logging.getLogger("ISF").getChild(__name__)


def _convert_neup_fns_to_reldb(neup, hoc_fn_map, recsites_fn_map):
    """Convert all paths in a :ref:`cell_parameters_format` file to point to a hash filename.
    
    See also:
        :py:meth:`~data_base.dbopen.resolve_neup_reldb_paths` to resolve the relative database paths in the neuron parameter file.
    """
    orig_hoc = neup["neuron"]["filename"]
    original_recsite_fns = neup["sim"]["recordingSites"]
    assert (
        orig_hoc in hoc_fn_map
    ), "The hoc file referenced in the neuron parameter file was not found:\n{}".format(
        orig_hoc
    )
    new_hoc_fn = hoc_fn_map[orig_hoc]
    rel_hoc_fn = create_reldb_path(new_hoc_fn)
    neup["neuron"]["filename"] = rel_hoc_fn

    for i, recsite_fn in enumerate(original_recsite_fns):
        assert (
            recsite_fn in recsites_fn_map
        ), "The recording site file referenced in the neuron parameter file was not found:\n{}".format(
            recsite_fn
        )
        new_recsite_fn = recsites_fn_map[recsite_fn]
        rel_recsite_fn = create_reldb_path(new_recsite_fn)
        neup["sim"]["recordingSites"][i] = rel_recsite_fn
    # if 'channels' in neuron['NMODL_mechanisms']:
    #    neuron['NMODL_mechanisms']['channels'] = os.path.join(target_dir, os.path.basename(neuron['NMODL_mechanisms']['channels']))
    return neup


def _convert_netp_fns_to_reldb(netp, syn_fn_map, con_fn_map):
    """Convert all paths in a :ref:`network_parameters_format` file to point to a hash filename.
    
    See also:
        :py:meth:`~data_base.dbopen.resolve_netp_reldb_paths` to resolve the relative database paths in the network parameter file.
    """
    for cell_type in list(netp["network"].keys()):
        if not "synapses" in netp["network"][cell_type]:
            continue
        orig_con = netp["network"][cell_type]["synapses"]["connectionFile"]
        orig_syn = netp["network"][cell_type]["synapses"]["distributionFile"]
        assert (
            orig_con in con_fn_map
        ), "The connection file referenced for {} in the network parameter file {} was not found:\n{}".format(
            cell_type, netp, orig_con
        )
        assert (
            orig_syn in syn_fn_map
        ), "The synapse file referenced for {} in the network parameter file {} was not found:\n{}".format(
            cell_type, netp, orig_syn
        )

        new_con_fn = con_fn_map[orig_con]
        new_syn_fn = syn_fn_map[orig_syn]
        rel_con_fn = create_reldb_path(new_con_fn)
        rel_syn_fn = create_reldb_path(new_syn_fn)

        netp["network"][cell_type]["synapses"]["connectionFile"] = rel_con_fn
        netp["network"][cell_type]["synapses"]["distributionFile"] = rel_syn_fn
    return netp


def _convert_syn_fns_to_reldb(syn_content, hoc_fn_map):
    """Copy, rename and transform a single :ref:`syn_file_format` file.

    The :ref:`syn_file_format` file is copied to the target directory, renamed to its hash, and the hoc file name is replaced.

    Args:
        syn_fn (str): Path to the synapse distribution file.
        new_hoc (str): Path to the new hoc file.
    """

    syn_content = syn_content.split("\n")
    # Use a regular expression to replace the .hoc file name
    matches = re.findall(r"\b\S+\.hoc\b", syn_content[1])
    if len(matches) == 0:
        logger.warning("No .hoc file reference in syn file")
        assert (
            len(hoc_fn_map) == 1
        ), "Found no .hoc file reference in the .syn file, but there are {} .hoc files in the original results directory. I don't know which .hoc file this .syn file i ssupposed to refer to.".format(
            len(hoc_fn_map)
        )
        # simply take the first and only hoc file
        target_hoc_file = list(hoc_fn_map.values())[0]
    else:
        assert (
            matches[0] in hoc_fn_map
        ), "The .hoc file {} referenced in the .syn file was not found in the .hoc filepath mapping".format(
            matches[0]
        )
        target_hoc_file = hoc_fn_map[matches[0]]

    relative_hoc_file = create_reldb_path(target_hoc_file)
    syn_content[1] = "# {}\n".format(relative_hoc_file)
    return "\n".join(syn_content)


def _convert_con_fns_to_reldb(con_content, syn_fn_map):
    con_content = con_content.split("\n")
    # Use a regular expression to replace the .syn file name
    matches = re.findall(r"\b\S+\.syn\b", con_content[1])

    # check if the .con file contains a reference to a .syn file. Not always necessary, but important for error handling.
    if len(matches) == 0:
        logger.warning("No .syn file reference in .con file")
        assert (
            len(syn_fn_map) == 1
        ), "Found no .syn file reference in the .con file, but there are {} .syn files in the original results directory. I don't know which .syn file this .con file is supposed to refer to.".format(
            len(syn_fn_map)
        )
        # simply take the first and only synapse file
        target_syn_file = list(syn_fn_map.values())[0]
    else:
        assert (
            matches[0] in syn_fn_map
        ), "The synapse file {} referenced in the .con file was not found in the synapse file map".format(
            matches[0]
        )
        target_syn_file = syn_fn_map[matches[0]]

    relative_syn_file = create_reldb_path(target_syn_file)
    con_content[1] = "# {}\n".format(relative_syn_file)
    return "\n".join(con_content)


def _create_db_path_print(path, replace_dict=None):
    """
    :skip-doc:

    .. deprecated:: 0.5.0
       This method is deprecated. From v0.4.0 onwards, all parameterfiles are copied to the database,
       eliminating the need for relative db://-style paths.
    """
    ## replace_dict: todo
    if replace_dict is None:
        replace_dict = {}
    try:
        return create_modular_db_path(path), True
    except DataBaseException as e:
        # print e
        return path, False