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
"""Build :ref:`network_parameters_format` from a template file.
A :ref:`network_parameters_format` template is a partially built :ref:`network_parameters_format` object that already contains info on:

- Synapse dynamics per cell type
- Ongoing activity per cell type
- Any additional preconfigured activity parameters (e.g. "offset")

It is assumed that the cell types in the template have no subcategorization per anatomical area.
It is also asusmed that the network embedding and activity information **does** have cell types defined per anatomical area, separated by an underscore.
"""
from __future__ import annotations
from typing import Dict, Any
from pathlib import Path
import logging
from .reader import read_nr_connected_cells_from_con
from .network_param_builder import NetworkParamBuilder
from single_cell_parser.parameters import NTParameterSet, build_parameters

from config.user.network_activity import NETWORK_PARAM_TEMPLATE_FN, ADDITIONAL_NETWORK_ACTIVITY_PARAMS, ACTIVITY_DATA_DIR
from config.isf_logging import logger as isf_logger

logger = isf_logger.getChild(suffix=__name__)


def _get_activity_data_from_globstring(
    match_str: str | None,
    activity_data_dir: str | Path,
) -> NTParameterSet:
        activity_fns = [f for f in Path(ACTIVITY_DATA_DIR).glob(pattern=f"*{match_str}*")]
        if len(activity_fns) > 1: raise ValueError(f"More than 1 file found matching {match_str} in {activity_data_dir}")
        elif len(activity_fns) == 0: raise ValueError(f"No file found matching {match_str} in {activity_data_dir}")
        else:
            activity_data_fn = activity_fns[0]
            logger.info(f"Using activity_data: {activity_data_fn}") 
        return build_parameters(activity_data_fn)



def build_network_param_from_template(
    template_fn: str | Path | None = None,
    cell_nr_fn = None, # unused, but we keep for backwards compatibility
    syn_fn: str | Path = None,
    con_fn: str | Path = None,
    activity_per_ct: str | NTParameterSet | None = None,
    out_fn: str | None = None,
    write_all_celltypes: bool = False,
    additional_activity_params: NTParameterSet | None = None,
    activity_data_dir: str | Path |None = None
) -> NTParameterSet:
    """Build :ref:`network_parameters_format` from a template.

    A :ref:`network_parameters_format` template is a partially built :ref:`network_parameters_format` object that already contains info on:

    - Synapse dynamics per cell type
    - Ongoing activity per cell type
    - Any additional preconfigured activity parameters (e.g. "offset")

    It is assumed that the cell types in the template have no subcategorization per anatomical area.
    It is also asusmed that the network embedding and activity information **does** have cell types defined per anatomical area, separated by an underscore.

    Example::

        >>> template.network.keys()
        ['type1', 'type2', ...]
        >>> netp = build_network_param_from_template(template, ...)
        >>> netp.keys()
        ['type1_area1' ... 'type2_area4' ...]

    Args:
        template_fn (str | :class:`pathlib.Path`): The name of the template file. If not given, defaults to the one configured in the user settings. Default: None (user settings fallback).
        syn_fn (str | :class:`pathlib.Path`): The name or Path to a :ref:`syn_file_format` file.
        con_fn (str | :class:`pathlib.Path`): The name or Path to a :ref:`con_file_format` file.
        activity_per_ct (dict | :class:`~single_cell_parser.parameters.NTParameterSet` | str): 
            Mapping between cell types and their corresponding activity data. Can e.g. be read from a :ref:`activity_data_format` file.
            If this is a string instead, it is interpreted as a globstring, and I look for activity data files in :param:`activity_data_dir`.
        activity_data_dir (str | :class:`pathlib.Path`):
            Directory containing :ref:`activity_data_format`. If not given, defaults to the one configured in the user settings. Default: None (user settings fallback).
        out_fn (str): Where to save the :ref:`network_parameters_format` to. Default: None (don't save).
        write_all_celltypes (bool): Whether to write out information of celltypes, even if they are not connected. Default: False.
        additional_activity_params (:class:`~single_cell_parser.parameters.NTParameterSet`):
            Additional network parameters to add.

    Returns:
        :class:`~single_cell_parser.parameters.NTParameterSet`: The :ref:`network_parameters_format`.


    .. deprecated 0.6.0::
       The :param:`cell_nr_fn` is deprecated and no longer needed. It may be removed in a future version.
    """

    if template_fn == None:
        logger.info(f"No network parameter template passed. Falling back to the default: {NETWORK_PARAM_TEMPLATE_FN}")    
        template_fn = NETWORK_PARAM_TEMPLATE_FN

    if cell_nr_fn is not None:
        logger.warning("The cell number filename is no longer needed, as all relevant info exists in the .con file Cell ID.")

    if activity_per_ct == None:
        logger.info(f"No network parameter template passed. Falling back to the default: {NETWORK_PARAM_TEMPLATE_FN}")    
        activity_per_ct = build_parameters()
    elif isinstance(activity_per_ct, str):
        logger.info("Activity is passed as a string instead of explicit data as an NTParameterSet")
        if activity_data_dir == None:
            logger.info(f"No data directory passed. Looking for activity data in the user-configure {ACTIVITY_DATA_DIR}")
            activity_data_dir = ACTIVITY_DATA_DIR
        else:
            logger.info(f"Looking for activity data in {activity_data_dir}")
        activity_per_ct = _get_activity_data_from_globstring(
            match_str=activity_per_ct,
            activity_data_dir=activity_data_dir
        )

    if additional_activity_params == None and len(ADDITIONAL_NETWORK_ACTIVITY_PARAMS) > 0:
        logger.info("No additional activity parameters passed, but the user config has them defined. Using the user-configured additional network parameters...")
        additional_activity_params = NTParameterSet(ADDITIONAL_NETWORK_ACTIVITY_PARAMS)


    template = build_parameters(filename=template_fn)

    # TODO document this function expects celltypes of the form ct_area
    celltypes_anareas = read_nr_connected_cells_from_con(con_fn).index.values
    celltypes = set([e.split("_")[0] for e in celltypes_anareas])
    anatomical_area = set([e.split("_")[-1] for e in celltypes_anareas])
    subcategorized_celltypes_map = {
        ct: [f"{ct}_{area}" for area in anatomical_area] 
        for ct in template.network.keys()
    }

    netp = NetworkParamBuilder(
        netp=template
    ).subcategorize_celltypes(
        cell_type_map = subcategorized_celltypes_map
    ).add_network_embedding(
        syn_fn = syn_fn,
        con_fn = con_fn,
    ).add_activity(
        activity_per_ct = activity_per_ct,
        additional_params = additional_activity_params,
    ).network_parameters

    if out_fn != None:
        netp.save(out_fn)

    return netp