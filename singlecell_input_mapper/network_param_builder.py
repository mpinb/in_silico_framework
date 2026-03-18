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

from config.model_system import EXCITATORY, INHIBITORY

logger: Logger = logging.getLogger(name="ISF").getChild(suffix=__name__)

syn_template_parent_dir = Path(getting_started.__file__).parent / "example_data" / "functional_constraints"
EXC_SYN_TEMPLATE = build_parameters(filename=syn_template_parent_dir / "exc_synapse_template.param")
INH_SYN_GENERIC = build_parameters(filename=syn_template_parent_dir / "inh_synapse_template.param")

class NetworkParamBuilder:
    # Build network parameters using a builder pattern
    # Not the most efficient, as you iterate all cell types multiple times, but way more clear what's happening
    # Normally, the amount of cell types is < O(100), so efficiency is not the biggest concern here.
    """

    For example, if we have ongoing activity defined per cell type, and additional evoked activity defined per cell type
    AND per anatomical area, we would do:

    Example::

        >>> 
    """
    def __init__(
        self,
        netp: NTParameterSet = None,
        write_all_celltypes: bool = False
    ) -> None:
        self.network_parameters: NTParameterSet = netp or NTParameterSet(
            data={
                "info": {},
                "network": {},
                "NMODL_mechanisms": {} # TODO
        })

        self.write_all_celltypes = write_all_celltypes
        self.contains_network_embedding_data = False
        self.contains_ongoing_activity_data = False
        self.contains_synapse_dynamics = False
        self.contains_evoked_activity_data = False


    def add_network_embedding(
        self,
        syn_fn,
        con_fn=None
        ) -> Self:
        if con_fn is None:
            logger.warning(msg="No .con filename passed. Assuming it has the same name as the .syn file...")
            con_fn = syn_fn[:-3] + "con"  # assume same name.
            assert os.path.exists(con_fn), "You did not pass a con_fn and I couldn't find it based on the .syn file. File does not exist: {}".format(con_fn)
        nr_cells = read_nr_connected_cells_from_con(con_fn)

        for celltype_anarea, nr_cells_this_ct in nr_cells.items():
            cell_type, anatomical_area = celltype_anarea.split("_")
            if nr_cells_this_ct == 0 and not self.write_all_celltypes: continue
            cell_type_name_full = cell_type + '_' + anatomical_area
            self.network_parameters.network.update(
                other=NTParameterSet({
                    cell_type_name_full: {
                        "cellNr": nr_cells_this_ct,
                        "synapses": {
                            "distributionFile": syn_fn,
                            "connectionFile": con_fn
                        }
                    }
                })
                )

        self.contains_network_embedding_data = True
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
        cell_type_synapse_map=None
        ) -> Self:
        """Add synapse dynamics to the :ref:`network_parameters_format`.

        Synapse dynamics parameters must have names that match 

        """
        if cell_type_synapse_map is None:
            logger.warning(msg="No cell type specific synapse dynamics passed. Using generic synapse dynamics for excitatory and inhibitory instead. These can be configured in the user config.")
            self._add_synapse_dynamics_generic()
        else:
            assert isinstance(cell_type_synapse_map, Mapping), "If passing specific synapse dynamics per cell type, please do so as a Mapping (e.g. a dict or NTParameterSet)."
            self.network_parameters.network.update(other=cell_type_synapse_map)

        self.contains_synapse_dynamics = True
        return self

    def add_ongoing_activity(
        self,
        ongoing_interval_per_ct: Mapping[str, float] = None,  # TODO: default value?
        **kwargs
        ) -> Self:
        """Add :ref:`ongoing_activity_data_format` to the :ref:`network_parameters_format`

        Ongoing activity is background activity, modeled as a Poisson ``"spiketrain"``. 
        It is distinct from evoked activity, which is modeled as a ``"pointcell"`` with multiple possible activity distributions 
        (see :meth:`~single_cell_parser.network.NetworkMapper._create_pointcell_activities`)

        Args:
            ongoing_rates_fn (str): 
                Filename of a .csv file containing the ongoing firing rates of all cell types. 
                Cell types must be of the form ``celltype[_<anatomical_area>]``,
                where ``celltype`` must exist in the configured celltypes, and ``_<anatomical_area>`` is an optional subdivision for these celltypes.
            includes_anatomical_area (bool): 
                Whether the :param:`ongoing_rates_fn` specifies ongoing activity per anatomical area or simply per cell type.
                If true, the cell types in :param:`ongoing_rates_fn` must be of the form ``<cell type>_<anatomical area>``
                Default is False, i.e. a cell type has the same onoging activity rate, independent of which anatomical area it is located in.
            kwargs: Additional keyword arguments to pass to :pd:meth:`read_csv`

        Attention:
            By default, ongoing firing rates are defined per cell type, but **not** per anatomical area (in contrast to e.g. evoked activity). 
            If you want to specify ongoing activity per anatomical area, remember to set :param:`includes_anatomical_area` to ``True``.

        Attention:
            Unless specified otherwise, the ongoing firing rates will be read with a tab separator and ``index_col=0`` by default.
            First column must contain the ongoing rates. Index column must be cell types.

        See also:
            :meth:`add_evoked_activity`
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
        self.contains_ongoing_activity_data = True

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
            ct_to_activity_fn_map (dict): 
                Dictionary mapping cell types to corresponding :ref:`activity_file_format` files, containing activity 
            key_modify_fun (callable): Function that takes a key and returns it changed.
            additional_evoked_params (dict | :class:`~single_cell_parser.parameters.NTParameterSet`):
                Additional parameters to add to the evoked network activity parameters. Useful for e.g. setting a time offset value. 

        See also:
            :meth:`add_ongoing_activity`
        """
        assert isinstance(activity_per_ct, Mapping), "Please provide a mapping between cell types and their activity data." 

        for celltype in self.network_parameters.network.keys():
            # Read PSTh data and add to netp
            psth = activity_per_ct.get(celltype, None)
            if psth == None:
                # No activity data for this cell type in the network params was found in the passed activity data
                # This is fine.
                continue
            self.network_parameters.network[celltype].celltype["pointcell"] = psth
            if additional_params is not None:
                self.network_parameters.network[celltype].celltype['pointcell'].update(additional_params)

        return self