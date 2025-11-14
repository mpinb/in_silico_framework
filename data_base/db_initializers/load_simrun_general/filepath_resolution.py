import logging
import os
import re

from data_base.dbopen import (
    create_modular_db_path,
    create_reldb_path,
    _find_parent_db,
    resolve_db_path,
)
from data_base.exceptions import DataBaseException
logger = logging.getLogger("ISF").getChild(__name__)


def _convert_neup_fns_to_reldb(neup, hoc_fn_map, recsites_fn_map):
    """Convert all paths in a :ref:`cell_parameters_format` file to point to a hash filename.

    See also:
        :func:`~data_base.dbopen.resolve_neup_reldb_paths` to resolve the relative database paths in the neuron parameter file.
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
        assert (recsite_fn in recsites_fn_map), "The recording site file referenced in the neuron parameter file was not found:\n{}".format(recsite_fn)
        new_recsite_fn = recsites_fn_map[recsite_fn]
        rel_recsite_fn = create_reldb_path(new_recsite_fn)
        neup["sim"]["recordingSites"][i] = rel_recsite_fn
    # if 'channels' in neuron['NMODL_mechanisms']:
    #    neuron['NMODL_mechanisms']['channels'] = os.path.join(target_dir, os.path.basename(neuron['NMODL_mechanisms']['channels']))
    return neup


def _convert_netp_fns_to_reldb(netp, syn_fn_map, con_fn_map):
    """Convert all paths in a :ref:`network_parameters_format` file to point to a hash filename.

    See also:
        :func:`~data_base.dbopen.resolve_netp_reldb_paths` to resolve the relative database paths in the network parameter file.
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
        syn_content (List[str]): Content of the :ref:`syn_file_format` file as a list of strings, each element representing a line.
        hoc_fn_map (str): Mapping from old to new :ref:`hoc_file_format` files.
    """

    def find_hoc_file(match):
        if match not in hoc_fn_map:
            hoc_fn_soft_matches = {k: v for k, v in hoc_fn_map.items() if match in k}
            if len(hoc_fn_soft_matches) == 1:
                return list(hoc_fn_soft_matches.values())[0]
            elif len(hoc_fn_soft_matches) > 1:
                logger.warning(
                    "The .hoc file referenced in the .syn file can refer to multiple .hoc files, so I will leave the reference unchanged.\n.hoc reference in .syn: {}\n Potential .hoc file candidates: {}".format(
                        match, hoc_fn_soft_matches.keys()
                    )
                )
                return match
            else:
                logger.warning(
                    "The .hoc file referenced in the .syn file was not found in the .hoc filepath mapping, so I will leave the reference unchanged\n.hoc reference in .syn: {}\n filepath mapping: {}".format(
                        match, hoc_fn_map
                    )
                )
                return match

    syn_content = syn_content.split("\n")
    # Use a regular expression to replace the .hoc file name
    matches = re.findall(r"\b\S+\.hoc\b", syn_content[1])
    if len(matches) == 0:
        logger.warning("No .hoc file reference in syn file")
        assert (len(hoc_fn_map) == 1), "Found no .hoc file reference in the .syn file, but there are {} .hoc files in the original results directory. I don't know which .hoc file this .syn file is supposed to refer to.".format(len(hoc_fn_map))
        # simply take the first and only hoc file
        original_hoc_file = list(hoc_fn_map.values())[0]
    elif len(matches) > 1:
        raise ValueError(
            "Found multiple .hoc references in the .syn file. This is not supported."
        )
    else:
        original_hoc_file = matches[0]
        if not os.path.isabs(original_hoc_file):
            original_hoc_file = find_hoc_file(original_hoc_file)
    if not os.path.isabs(original_hoc_file): relative_hoc_file = original_hoc_file
    else: relative_hoc_file = create_reldb_path(original_hoc_file)
    syn_content[1] = "# {}\n".format(relative_hoc_file)
    return "\n".join(syn_content)


def _convert_con_fns_to_reldb(con_content, syn_fn_map, con_fn):
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
        if not os.path.isabs(matches[0]):
            abs_fn = _resolve_syncon_ref(con_fn, matches[0])
        else: abs_fn = matches[0]
        target_syn_file = syn_fn_map[abs_fn]

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


def _resolve_rel_syncon_ref(fn, ref):
    """Resolve a relative database style path of .syn or .con files

    Args:
        fn (str): The filename containing the reference
        ref (str): The relative reference to a .syn or .con file.

    Returns:
        str: The absolute path to the referenced file.
    """
    assert ref.startswith("reldb://")
    db_basedir = _find_parent_db(fn)
    abs_ref = resolve_db_path(ref, db_basedir=db_basedir)
    return abs_ref

def _resolve_syncon_ref(fn, ref):
    """Resolve relative references in :ref:`syn_file_format` or :ref:`conf_file_format` files.

    Relative references can either be filenmaes without preceding directory structure, or reldb://-style relative paths.
    """
    if ref.startswith("reldb://"): 
        abs_fn = _resolve_rel_syncon_ref(fn, ref)
    else:
        dir_path = os.path.dirname(fn)
        abs_fn = os.path.join(dir_path, ref)
    assert os.path.exists(
        abs_fn
    ), "The .syn file referenced in the .con file was not found:\n{}".format(abs_fn)
    return abs_fn