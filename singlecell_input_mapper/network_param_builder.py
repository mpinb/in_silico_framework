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
"""Builder object for :ref:`network_parameters_format`.
"""
from __future__ import annotations # so I can typehing the class lazily
from logging import Logger
from typing_extensions import Self
from typing import Any, Iterable, Dict
from collections.abc import Mapping

from single_cell_parser.parameters import NTParameterSet
from single_cell_parser.parameters import build_parameters
import pandas as pd
from .reader import read_nr_connected_cells_from_con
import logging
import re, os
from pathlib import Path
import getting_started
import copy

from config.user.cell_types import EXCITATORY, INHIBITORY

logger: Logger = logging.getLogger(name="ISF").getChild(suffix=__name__)

syn_template_parent_dir = Path(getting_started.__file__).parent / "example_data" / "functional_constraints"
EXC_SYN_TEMPLATE = build_parameters(filename=syn_template_parent_dir / "exc_synapse_template.param")
INH_SYN_GENERIC = build_parameters(filename=syn_template_parent_dir / "inh_synapse_template.param")

class NetworkParamBuilder:
    # Build network parameters using a builder pattern
    # Not the most efficient, as you iterate all cell types multiple times, but way more clear what's happening
    # Normally, the amount of cell types is < O(100), so efficiency is not the biggest concern here.
    """Builder for :ref:`network_parameters_format`.

    This class adds network data to a :class:`~single_cell_parser.paramters.NTParameterSet`.
    Network data can include:

    - Network embedding data (locations of synapses on the dendrite and their presynaptic origin, i.e. :ref:`syn_file_format` and :ref:`con_file_format` files)
    - Activity data (i.e. when does each presynaptic cell activate)
    - Synapse dynamics
    - Any relevant additional information, such as a stimulus "offset"


    Example::

        netpb = NetworkParamBuilder(
        ).add_ongoing_activity(
            ongoing_interval_per_ct = celltype_to_ongoing_map
        ).add_synapse_dynamics(
        ).subcategorize_celltypes(
            cell_type_map = subcategorized_celltypes_map
        ).add_network_embedding(
            syn_fn = syn_fn,
            con_fn = con_fn,
        ).add_activity(
            activity_per_ct   = activity_data_per_subct,
            additional_params = additional_evoked_parameters
        ).network_parameters

        netp.save(
            filename=save_filename
        )
    """
    def __init__(
        self,
        netp: NetworkParamBuilder | NTParameterSet | None = None,
        embedding_include_all_celltypes: bool = False
    ) -> None:
        """
        Args:
            netp (:class:`~single_cell_parser.parameters.NTParameterSet`):
                An existing :ref:`network_parameters_format` object.
                If not given, a new one is initialized from scratch.
            embedding_include_all_celltypes (bool): 
                Whether to write network embedding information for all cell types, even if they are not connected
                to the postsynaptic cell.
                Default is False
        """
        if netp == None:
            self.network_parameters = NTParameterSet(
                data={
                    "info": self._generate_param_info(),
                    "network": {},
                    "NMODL_mechanisms": {} # TODO
            })
        elif isinstance(netp, NTParameterSet):
            self.network_parameters = netp
        elif isinstance(netp, NetworkParamBuilder):
            self.network_parameters = netp.network_parameters
        else:
            raise ValueError(f"Could not instantiate a NetworkParamBuilder from an object of type {type(netp)}")

        self.write_all_celltypes = embedding_include_all_celltypes


    def _generate_param_info(self):
        """Generate basic info for the :ref:`network_parameters_format`

        The info includes:

        - The creation date
        - The name of the user
        """
        from datetime import datetime
        import getpass
        return {
            "date": datetime.today().strftime('%Y-%m-%d'),
            "name": getpass.getuser()
        }

    def add_network_embedding(
        self,
        syn_fn,
        con_fn=None,
        join="left"
        ) -> Self:
        """Add network embedding data.

        Args:
            syn_fn (str): Path to the :ref:`syn_file_format` file
            con_fn (str): Path to the :ref:`con_file_format` file. 
                If not given, it is assumed it has the same name and location as the :ref:`syn_file_format` file, and only the suffix is different.
                Default: None.
            join (str):
                How to join the information for each cell type. Options are:

                - "left": Fetch connectivity info for each cell type already present in the network parameters i.e. left-join the incoming connectivity data.
                - "right" Fetch connectivity info for each cell type present in the incoming :ref:`syn_file_format` and :ref:`con_file_format` files, and add them (non-destructively) to the parameters, independent of whether they already exist or not i.e. right-join the incoming connectivity data.
        """
        if con_fn is None:
            logger.warning(msg="No .con filename passed. Assuming it has the same name as the .syn file...")
            con_fn = syn_fn[:-3] + "con"  # assume same name.
            assert os.path.exists(con_fn), "You did not pass a con_fn and I couldn't find it based on the .syn file. File does not exist: {}".format(con_fn)
        nr_cells = read_nr_connected_cells_from_con(con_fn)

        mark_celltype_for_deletion = []

        if join == "left": celltypes = self.network_parameters_network.keys()
        elif join == "right": celltypes = nr_cells.index

        for celltype in celltypes:
            if not celltype in nr_cells:
                if not self.write_all_celltypes:
                    mark_celltype_for_deletion.append(celltype)
                    continue
            nr_cells_this_ct = int(nr_cells.get(celltype, 0))
            
            self.network_parameters.network.update(
                other=NTParameterSet({
                    celltype: {
                        "cellNr": nr_cells_this_ct,
                        "synapses": {
                            "distributionFile": syn_fn,
                            "connectionFile": con_fn
                        }
                    }
                })
                )

        for ct in mark_celltype_for_deletion:
            self.network_parameters.network.pop(ct)

        return self

    def subcategorize_celltypes(
        self,
        cell_type_map: Dict[str, Iterable[str]] = None
        ) -> Self:
        """Subgategorize cell types in the :ref:`network_parameters_format` file.

        This is useful for workflows where some presynaptic cell type attributes are defined on an aggregate level.
        That way, you can set them on an aggregate level, subcategorize the :ref:`network_parameters_format`, and 
        set the more specific cell types afterwards.

        Args:
            cell_type_map (dict): Mapping between existing cell types in the :ref:`network_parameters_format` and the subcategorized cell types.


        Example::

            >>> netp.network.keys()
            ["L1", "L2", ...]
            >>> netp = NetworkParamBuilder(netp).subcategorize_celltypes(
                    {
                        "L1": ["L1_A1", "L1_A2", ...]
                    }
                )
            >>> netp.network.keys()
            ["L1", "L2_A1", "L2_A2" ...]

        """

        netw_params = self.network_parameters.network

        new_netw_params = {}
        for ct, value in netw_params.items():
            subcts = cell_type_map.get(ct)
            if subcts is None:
                logger.warning("Cell type {} found in existing network parameters, but not in the mapping you provided for subcategorization".format(ct))
                new_netw_params[ct] = value  # preserve unmapped types as-is
            else:
                for subct in subcts:
                    # Make a copy, otherwise all subcategories share the same reference. Updating one would update all...
                    new_netw_params[subct] = copy.deepcopy(value)

        self.network_parameters.network = new_netw_params
        return self

    def _add_synapse_dynamics_generic(
        self,
        ):
        """Add synapse dynamics based on EXC/INH

        Infers if the cell type is excitatory or inhibitory (based on the user configuration), and assigns
        generic glutamate and GABA-ergic receptors instead.

        See also:
            :meth:`add_synapse_dynamics`
        """
        if len(self.network_parameters.network.keys()) == 0: raise RuntimeError(
            "No cell types found in the network parameters. Can't infer generic synapse dynamics if I don't know for which cell types. " +
            "Please add cell types first by adding e.g. activity data or network embedding data"
            )
        for celltype in self.network_parameters.network:
            if celltype in EXCITATORY: syn = EXC_SYN_TEMPLATE
            elif celltype in INHIBITORY: syn = INH_SYN_GENERIC
            else: raise KeyError("Could not find the cell type \"{}\" in the configured excitatory or inhibitory cell types".format(celltype))
            self.network_parameters.network[celltype].update(syn)

    def add_synapse_dynamics(
        self,
        synapse_params_per_ct=None
        ) -> Self:
        """Add synapse dynamics to the :ref:`network_parameters_format`.

        Args:
            synapse_params_per_ct (dict | :class:`~single_cell_parser.parameters.NTParameterSet`):
                Mapping between cell types and synapse parameters. If none are given, this method 
                infers if the cell type is excitatory or inhibitory (based on the user configuration), and assigns
                generic glutamate and GABA-ergic receptors instead.

        See also:
            :meth:`_add_synapse_dynamics_generic`
        """
        if synapse_params_per_ct is None:
            logger.warning(msg="No cell type specific synapse dynamics passed. Using generic synapse dynamics for excitatory and inhibitory instead. These can be configured in the user config.")
            self._add_synapse_dynamics_generic()
        else:
            assert isinstance(synapse_params_per_ct, Mapping), "If passing specific synapse dynamics per cell type, please do so as a Mapping (e.g. a dict or NTParameterSet)."
            self.network_parameters.network.update(other=synapse_params_per_ct)

        return self

    def add_ongoing_activity(
        self,
        ongoing_interval_per_ct: Mapping[str, float] = None,
        ) -> Self:
        """Add :ref:`ongoing_activity_data_format` to the :ref:`network_parameters_format`

        Ongoing activity is background activity, modeled as a Poisson ``"spiketrain"``. 
        It is distinct from evoked activity, which is modeled as a ``"pointcell"`` with multiple possible activity distributions 
        (see :meth:`~single_cell_parser.network.NetworkMapper._create_pointcell_activities`)

        Args:
            ongoing_interval_per_ct (str): Mapping between cell types and their ongoing firing interval in ms

        See also:
            :meth:`add_activity` for a general-purpose method of adding activity data.
        """
        for celltype in ongoing_interval_per_ct:
            self.network_parameters.network.update(
                other={
                    celltype: {
                        "celltype": {
                            "spiketrain": {
                                "interval": ongoing_interval_per_ct[celltype]
                            }
                        }
                    }})
        return self

    def add_activity(
        self,
        activity_per_ct=None,
        additional_params=None
        ) -> Self:
        """
        Add :ref:`activity_data_format` to a :ref:`network_parameters_format` file.
        
        Evoked activity is network activity that is modeled as a ``"pointcell"`` with multiple possible activity distributions 
        (see :meth:`~single_cell_parser.network.NetworkMapper._create_pointcell_activities`).
        It is distinct form ongoing activity, which is modeled as a Poisson ``"spiketrain"``.
        
        Args:
            activity_per_ct (dict | :class:`~single_cell_parser.parameters.NTParameterSet`): 
                Mapping between cell types and their corresponding activity data. Can e.g. be read from a :ref:`activity_data_format` file.
            additional_params (dict | :class:`~single_cell_parser.parameters.NTParameterSet`):
                Additional parameters to add to the evoked network activity parameters. Useful for e.g. setting a time offset value. 

        See also:
            :meth:`add_ongoing_activity`
        """
        assert isinstance(activity_per_ct, Mapping), "Please provide a mapping between cell types and their activity data." 
        keys_in_data_not_in_netp = [k for k in activity_per_ct.keys() if k not in self.network_parameters.network]
        keys_in_netp_not_in_data = [k for k in self.network_parameters.network if k not in activity_per_ct.keys()]
        if len(keys_in_data_not_in_netp) > 1: 
            logger.debug(msg=f"Found {len(keys_in_data_not_in_netp)} keys in the passed activity data not present in the netwok paramters: {keys_in_data_not_in_netp}")
            logger.debug(msg="This likely means that you already added anatomical embedding data, while omitting non-connected cells. This is OK.")
        if len(keys_in_netp_not_in_data) > 1:
            # Cells are allowed to be connected or otherwise appear in the network params, and not in the activity data.
            # Either activity data is passed one by one, each time defining a subset of cell types, or these cells simply don't have activity. This is OK.
            logger.debug(msg=f"{len(keys_in_netp_not_in_data)} cell types in the network parameters do not appear in the passed activity data: {keys_in_netp_not_in_data}")

        for celltype in self.network_parameters.network.keys():
            # Read PSTh data and add to netp
            psth = activity_per_ct.get(celltype, None)
            if psth == None:
                # No activity data for this cell type in the network params was found in the passed activity data
                # This is fine.
                continue
            if self._has_flat_ongoing_activity(celltype): self._convert_flat_to_nested_ongoing_activity(celltype)
            self.network_parameters.network[celltype].celltype["pointcell"] = psth
            if additional_params is not None:
                self.network_parameters.network[celltype].celltype['pointcell'].update(additional_params)

        return self

    def _convert_flat_to_nested_ongoing_activity(self, celltype):
        """Convert flat ongoing activity to a nested format.

        Args:
            celltype (str): Which celltype to convert ongoing activity for.
        """
        interval = self.network_parameters.network[celltype].pop("interval")
        self.network_parameters.network[celltype].celltype = {
            'spiketrain': {
                'interval': interval
            }
        }

    def _has_flat_ongoing_activity(self, celltype):
        """Check if the :ref:`network_parameters_format` has ongoing activity in flat format.
        
        Some older :ref:`network_parameters_format' have ongoing activity data in a format that is
        incompatible with adding multiple sources of activity afterwards::

            <cell_type>: {
                'cell_type': 'spiketrain',
                'interval': int,
            }

        Ideally, the 'cell_type' key contains a dictionary, which in turn contains all sources of activity. Not a string "spiketrain".
        This function checks if the flat hierarchy exists.

        See also:
            :meth:`~_nest_existing_ongoing_activity_data` to transform this to a nested hierarchy, compatible
            with adding multiple sources of activity data.
        """
        return self.network_parameters.network[celltype].celltype == "spiketrain"
        