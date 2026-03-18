from __future__ import annotations
from typing import Dict, Any
from pathlib import Path
import logging
from .reader import read_nr_connected_cells_from_con
from .network_param_builder import NetworkParamBuilder
from single_cell_parser.parameters import NTParameterSet, build_parameters

from config.user.network_activity import ACTIVITY_DATA_MAP, NETWORK_PARAM_TEMPLATE_FN, ADDITIONAL_NETWORK_ACTIVITY_PARAMS
from config.isf_logging import logger as isf_logger

logger = isf_logger.getChild(suffix=__name__)


def build_network_param_from_template(
    template_fn: str | Path | None = None,
    cell_nr_fn = None, # unused, but we keep for backwards compatibility
    syn_fn: str | Path = None,
    con_fn: str | Path = None,
    activity_per_ct: str | NTParameterSet | None = None,
    out_fn: str | None = None,
    write_all_celltypes: bool = False,
    additional_activity_params: NTParameterSet | None = None
) -> NTParameterSet:
    """Build :ref:`network_parameters_format` from a template.

    """

    if template_fn == None:
        logger.attention(f"No network parameter template passed. Falling back to the default: {NETWORK_PARAM_TEMPLATE_FN}")    
        template_fn = NETWORK_PARAM_TEMPLATE_FN

    if activity_per_ct == None:
        logger.attention(f"No network parameter template passed. Falling back to the default: {NETWORK_PARAM_TEMPLATE_FN}")    
        activity_per_ct = build_parameters()
    elif isinstance(activity_per_ct, str):
        logger.attention("Activity is passed as a string. Looking for corresponding activity data in the user-configured data locations.")
        activity_per_ct = build_parameters(
            ACTIVITY_DATA_MAP[activity_per_ct]
        )

    if additional_activity_params == None and len(ADDITIONAL_NETWORK_ACTIVITY_PARAMS) > 0:
        logger.attention("No additional activity parameters passed, but the user config has them defined. Using the user-configured additional network parameters...")
        additional_activity_params = NTParameterSet(ADDITIONAL_NETWORK_ACTIVITY_PARAMS)


    template = build_parameters(filename=template_fn)

    celltypes_anareas = read_nr_connected_cells_from_con(con_fn).index.values
    celltypes = set([e.split("_")[0] for e in celltypes_anareas])
    subcategorized_celltypes_map = {
        ct: [subct for subct in celltypes_anareas if subct.startswith(ct)] 
        for ct in celltypes
    }

    netp = NetworkParamBuilder(
        netp=template
    ).subcategorize_celltypes(
        cell_type_map = subcategorized_celltypes_map
    ).add_network_embedding(
        syn_fn = syn_fn,
        con_fn = con_fn,
    ).add_activity(
        activity_per_ct=activity_per_ct,
        additional_params = additional_activity_params,
    ).network_parameters

    if out_fn != None:
        netp.save(out_fn)

    return netp