#!/usr/bin/python
# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Runfile to create a :ref:`network_parameters_format` file that captures the population activity of a rat barrel cortex during passive whisker touch in anasthesized animals.

Reads in a template parameter file and sets the PSTHs for each celltype to the PSTHs of the evoked activity.
Such PSTHs can be computed from spike time recordings using e.g. :mod:`~singlecell_input_mapper.evoked_PSTH_from_spike_times`.

Attention:
    This module is specific to the model of the rat barrel cortex and the experimental conditions of the passive whisker touch experiment.
    It is not intended to be used for other models or experiments.
    However, it may serve as a template for other experimental conditions.
"""
import sys, os
import single_cell_parser as scp
import getting_started
import pandas as pd
import logging

from . import load_cell_number_file

logger = logging.getLogger("ISF").getChild(__name__)

__author__ = ["Robert Egger", "Bjorge Meulemeester"]

evokedPrefix = os.path.join(
    getting_started.parent,
    'example_data',
    'functional_constraints',
    'evoked_activity') + '/'


CELL_TYPE_TO_ACTIVITY_FN_MAP = {
    'L2':       evokedPrefix + 'L2_3x3_PSTH_UpState.param',
    'L34':      evokedPrefix + 'L34_3x3_PSTH_UpState.param',
    'L4py':     evokedPrefix + 'L4py_3x3_PSTH_UpState.param',
    'L4sp':     evokedPrefix + 'L4sp_3x3_PSTH_UpState.param',
    'L4ss':     evokedPrefix + 'L4ss_3x3_PSTH_UpState.param',
    'L5st':     evokedPrefix + 'L5st_3x3_PSTH_UpState.param',
    'L5tt':     evokedPrefix + 'L5tt_3x3_PSTH_UpState.param',
    'L6cc':     evokedPrefix + 'L6cc_3x3_PSTH_UpState.param',
    'L6ccinv':  evokedPrefix + 'L6ccinv_3x3_PSTH_UpState.param',
    'L6ct':     evokedPrefix + 'L6ct_3x3_PSTH_UpState.param',
    'VPM':      evokedPrefix + 'VPM_3x3_PSTH.param',
    'L1':       evokedPrefix + 'L1_3x3_PSTH_template_PW_0-50_10ms.param',
    'L23Trans': evokedPrefix + 'L23Trans_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'L45Peak':  evokedPrefix + 'L45Peak_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'L45Sym':   evokedPrefix + 'L45Sym_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'L56Trans': evokedPrefix + 'L56Trans_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal1':evokedPrefix + 'SymLocal1_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal2':evokedPrefix + 'SymLocal2_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal3':evokedPrefix + 'SymLocal3_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal4':evokedPrefix + 'SymLocal4_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal5':evokedPrefix + 'SymLocal5_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
    'SymLocal6':evokedPrefix + 'SymLocal6_PSTH_active_timing_normalized_PW_1.0_SuW_0.5.param',
}




DEFLECTION_OFFSET = 245.0  #ms; to allow same analysis as CDK JPhys 2007
#deflectionOffset = 345.0 #ms; model2 needs more time to get to steady state


# TODO WIP: this creates identical results. Now we can refactor for easier input of other data
# TODO: idea: per-package config for package-specific config?
# TODO: explain how key_modify_fun works
def build_evoked_network_activity(
    netp_template_fn,
    nr_connected_cells_fn,
    syn_fn,
    con_fn,
    out_fn,
    ct_to_activity_fn_map = None,  # TODO: auto read from config?
    key_modify_fun = None,
    additional_netp_params = None, # TODO: cleaner way for this
    write_all_celltypes = False 
    ):
    """Generate and write out a :ref:`network_parameters_format` file defining the evoked activity of a passive whisker touch scenario.
    
    Reads in a template file for a network, where the parameters of each celltype are already defined, but the values are not set.
    Sets the PSTHs (i.e. spike probability per temporal bin) for each cell in the network, depending on the celltype, columnm, and which :param:`whisker` was deflected.
    Spike probabilities only depend on the celltype, column, and deflected whisker.
    Spike times are then Poisson sampled from these PSTHs.
    A spike does not guarantee a synapse relase, but rather the probability of release upon a spike is set for each celltype.
    
    The template file contains the key "network" with the following info for each celltype:
    
        - celltype: 'spiketrain' or 'pointcell'
        - interval: spike interval
        - synapses: containing receptor information (type, weight and time dynamics) and release probability
            - receptors
                - receptor type
                    - threshold: threshold for activation
                    - delay: delay for activation
                    - weight: weight of the synapse
        - releaseProb: probability that a synapse gets activated if the cell spikes
            
    Args:
        netp_template_fn (str): Name of the template parameter file.
        nr_connected_cells_fn (str): Name of the file containing the number of cells for each celltype and column.
            Normally, this is created by the network embedding pipeline
        syn_fn (str) : Name of the :ref:`syn_file_format` file, defining the synapse types.
        con_fn (str): Name of the :ref:`con_file_format` file, defining the connections.
        out_fn (str): Name of the output file.
        ct_to_activity_fn_map (dict): 
            Dictionary mapping anatomical areas to cell types to a corresponding :ref:`activity_file_format` file.
        key_modify_fun (callable): Function that takes a key and returns it changed.
        
    Example:
    
        >>> activity_file_map = {"column_A1": {"L5tt": activity_l5tt.param}, ...}

    """
    assert key_modify_fun is None or callable(key_modify_fun), "If passing a value for redirect_cell_type, it must be a function that takes a celltype string and returns it changed."
    ct_to_activity_fn_map = ct_to_activity_fn_map or CELL_TYPE_TO_ACTIVITY_FN_MAP
    if additional_netp_params == None: additional_netp_params = {"offset": DEFLECTION_OFFSET}  # TODO maybe move to config?

    logger.info('*************')
    logger.info('creating network parameter file from template {:s}'.format(netp_template_fn))
    logger.info('*************')

    template_param = scp.build_parameters(netp_template_fn)
    df_connected_cells = load_cell_number_file(nr_connected_cells_fn)

    netp = scp.NTParameterSet({
        'info': template_param.info,
        'NMODL_mechanisms': template_param.NMODL_mechanisms,
        'network': {}
    })

    def add_psth_to_netp(netp, psth):
        interval = netp.network[cell_type_full_name].pop('interval')
        netp.network[cell_type_full_name].celltype = {
            'spiketrain': {
                'interval': interval
            }
        }
        netp.network[cell_type_full_name].celltype['pointcell'] = psth
        netp.network[cell_type_full_name].celltype['pointcell'].update(additional_netp_params)
        return netp

    for anatomical_area in df_connected_cells:
        for cell_type in template_param.network:
            n_connected_cells = df_connected_cells[anatomical_area][cell_type]
            if n_connected_cells == 0 and not write_all_celltypes: continue
            activity_param_fn = ct_to_activity_fn_map[cell_type]

            cell_type_full_name = cell_type + '_' + anatomical_area
            cellTypeParameters = template_param.network[cell_type]
            netp.network[cell_type_full_name] = cellTypeParameters.tree_copy()

            # Read PSTh data and add to netp
            if key_modify_fun is not None:
                activity_data_key = key_modify_fun(cell_type_full_name)
            else:
                activity_data_key = cell_type_full_name
            if activity_data_key == None: 
                PSTH_params = None
            else:  
                PSTH_params = read_evoked_PSTH(fn=activity_param_fn, key=activity_data_key)
            if PSTH_params is not None: 
                netp = add_psth_to_netp(netp, psth=PSTH_params)

            n_connected_cells = df_connected_cells[anatomical_area][cell_type]
            netp.network[cell_type_full_name].cellNr = n_connected_cells
            netp.network[cell_type_full_name].synapses.distributionFile = syn_fn
            netp.network[cell_type_full_name].synapses.connectionFile = con_fn

    netp.save(filename=out_fn)


def read_evoked_PSTH(fn, key):
    """
    Fetch the PSTHs of each celltype in a barrel cortex :param:`column` for evoked activity reflecting 
    a passive whisker touch scenario.
    This method does not generate such data, but reads it in from existing files containing such empirical measurements, 
    and parses it. These existing data files are set as global variables in this runfile. For other activity data, adapt these file names.
    
    The data linked in this runfile are for experiments where the C2 whisker was deflected.
    For situations where other :param:`deflectedwhisker` are requested, activity data of equivalent
    columns relative to the C2 is requested.
    
    Example:
        >>> column = 'B2'  # I want activity from B2 column
        >>> deflectedWhisker = 'C1'  # I want activity reflecting deflection of C1 whisker (not C2)
        >>> cellType = 'L6ct'
        >>> params = whisker_evoked_PSTH(column=column, deflectedWhisker=deflectedWhisker, cellType=cellType)
        >>> print(params)  # This is activity data from the C3 column for C2 whisker deflection i.e. equivalent activity
        {
            'distribution': 'PSTH', 
            'intervals': [(40.0, 41.0), (43.0, 44.0), (49.0, 50.0)], 
            'probabilities': [0.0057, 0.0057, 0.0057]
            }

    Args:
        cellType (str): Which cell type you want the PSTH for.

    Returns:
        parameters.NTParameterSet: 
            The PSTH for the given cell type in a C2-relative equivalent column, reflecting the deflection of the given whisker.
    """
    cell_type_evoked_activity = scp.build_parameters(fn) 
    PSTH = cell_type_evoked_activity.get(key)
    return PSTH



if __name__ == '__main__':
    #    if len(sys.argv) == 7:
    if len(sys.argv) == 6:
        templateParamName = sys.argv[1]
        cellNumberFileName = sys.argv[2]
        synFileName = sys.argv[3]
        #        conFileName = sys.argv[4]
        conFileName = synFileName[:-4] + '.con'
        whisker = sys.argv[4]
        outFileName = sys.argv[5]
        create_network_parameter(templateParamName, cellNumberFileName,
                                 synFileName, conFileName, whisker, outFileName)
    else:
        #        print 'parameters: [templateParamName] [cellNumberFileName] [synFileName] [conFileName] [deflected whisker] [outFileName]'
        print(
            'parameters: [ongoingTemplateParamName] [cellNumberFileName] [synFileName (absolute path)] [deflected whisker] [outFileName]'
        )
