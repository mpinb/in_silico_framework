import os
import numpy as np
from pathlib import Path
from single_cell_parser.parameters import fast_extract_values_from_param_file_key
from config.isf_logging import logger


def get_filter_healthy_simresult_dirs(sim_result_dirs, client=None):
    if client is not None:
        f = client.map(check_is_simresult_dir_healthy, sim_result_dirs)
        is_healthy_mask = client.gather(f)
    else:
        is_healthy_mask = [check_is_simresult_dir_healthy(p) for p in sim_result_dirs]
    
    is_healthy_mask = np.array(is_healthy_mask)
    if any(~is_healthy_mask):
        n_unhealthy = sum(~is_healthy_mask)
        logger.warning("{} out of {} simulation results are incomplete ({:2f}%)".format(
            n_unhealthy, len(sim_result_dirs), n_unhealthy*100/len(sim_result_dirs)))
    is_healthy_mask = np.array(is_healthy_mask)
    return is_healthy_mask


def check_is_simresult_dir_healthy(sim_result_dir):
    sim_result_dir = Path(sim_result_dir)
    if not _check_params_exist(sim_result_dir): return False
    if not _check_n_vts_match(sim_result_dir): return False
    if not _check_param_files_have_working_refs(sim_result_dir): return False
    return True


def _check_params_exist(sim_result_dir):
    # Check if all param files exist
    netp = sim_result_dir.glob("*network_*.param")
    neup = sim_result_dir.glob("*neuron_*.param")
    if not any(netp):
        logger.error(f"No network .param file found in {sim_result_dir}")
        return False
    if not any(neup):
        logger.error(f"No neuron .param file found in {sim_result_dir}")
        return False
    return True


def _read_n_traces(vt_csv_file, sep='\t'):
    with open(vt_csv_file, 'r') as f:
        header = f.readline().strip()
    return len(header.split(sep)) - 1



def _check_n_vts_match(sim_result_dir):
    # N somatic voltage traces
    vt_file_glob = list(sim_result_dir.glob("*vm_all_traces*"))
    if not any(vt_file_glob):
        logger.error(f"No somatic voltage traces found in {sim_result_dir}")
        return False
    if any(['.npz' in e.suffixes for e in vt_file_glob]):
        logger.warning(f"Found a .npz voltage trace files at {sim_result_dir}. I don't know how to check how many traces there are. Assuming the amount of traces matches other files in this directory and continuing.")
    n_soma_traces = sum([_read_n_traces(f) for f in vt_file_glob if ".npz" not in f.suffixes])
    
    # N dendritic voltage traces
    vt_dend_file_glob = list(sim_result_dir.glob("*vm_dend_traces*"))
    if not any(vt_dend_file_glob):
        logger.error(f"No somatic voltage traces found in {sim_result_dir}")
        return False
    if any([".npz" in e.suffixes for e in vt_dend_file_glob]):
        logger.warning(f"Found a .npz voltage trace files at {sim_result_dir}. I don't know how to check how many traces there are. Assuming the amount of traces matches other files in this directory and continuing.")
    n_dend_traces = [_read_n_traces(f) for f in vt_dend_file_glob if ".npz" not in f.suffixes]

    # N presyn activation and cell activation files
    n_presyn_csv_files = sum([1 for _ in sim_result_dir.glob("*_presynaptic_cells*")])
    n_syn_csv_files = sum([1 for _ in sim_result_dir.glob("*_synapses*")])
    
    # Check if they are all the same
    if not len(set([n_soma_traces, *n_dend_traces, n_presyn_csv_files, n_syn_csv_files])) == 1:
        logger.error(f"Found an inconsistent filecount in {sim_result_dir}: {n_soma_traces} somatic vts, {n_dend_traces} dendritic vts, {n_presyn_csv_files} presynaptic activation files, and {n_syn_csv_files} synapse activation files. I don't know which vt belongs to which other file.")
        return False

    return True


def _check_netp_has_working_refs(netp_fn):
    syn_fns, con_fns = fast_extract_values_from_param_file_key(netp_fn, ['distributionFile', 'connectionFile'])
    syn_exist_mask = [os.path.exists(e) for e in syn_fns]
    if not all(syn_exist_mask):
        logger.error(f"Found .syn file references in {netp_fn} that do not exist: {syn_fns[syn_exist_mask]}")
        return False
    con_exist_mask = [os.path.exists(e) for e in con_fns]
    if not all(con_exist_mask):
        logger.error(f"Found .con file references in {netp_fn} that do not exist: {con_fns[con_exist_mask]}")
        return False
    return True


def _check_neup_has_working_refs(neup_fn):
    morph_fns, = fast_extract_values_from_param_file_key(neup_fn, ['filename'])
    recsites_fns, = fast_extract_values_from_param_file_key(neup_fn, ['recordingSites'])
    if not len(morph_fns) == 1:
        logger.error(f"Found {len(morph_fns)} morphology references in {neup_fn}, expected 1.")
        return False
    morph_fn = morph_fns[0]
    assert not len(recsites_fns) > 1, f"recSites key is defined multiple times in {neup_fn}"
    if not Path(morph_fn).exists():
        logger.error(f"The morphology reference in {neup_fn} does not exist: {morph_fn}")
        return False
    for recsites_fn_list in recsites_fns:
        for recsite_fn in recsites_fn_list:
            if not Path(recsite_fn).exists():
                logger.error(f"The recsite .landmarkAscii reference in {neup_fn} does not exist: {recsite_fn}")
                return False
    return True

def _check_param_files_have_working_refs(sim_result_dir):
    neup_fn = list(sim_result_dir.glob("*_neuron*.param"))[0]
    neup_has_working_refs_bool = _check_neup_has_working_refs(neup_fn)
    
    netp_fn = list(sim_result_dir.glob("*_network*.param"))[0]
    netp_has_working_refs_bool = _check_netp_has_working_refs(netp_fn)

    return neup_has_working_refs_bool and netp_has_working_refs_bool
    