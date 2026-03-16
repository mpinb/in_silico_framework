import single_cell_parser as scp
import pandas as pd
from .reader import read_cell_number_file, read_evoked_PSTH
import logging
import re
from pathlib import Path
from collections.abc import Mapping

from config.model_system import EXCITATORY, INHIBITORY

logger = logging.getLogger(name="ISF").getChild(suffix=__name__)

class NetworkParamBuilder:
    # Build network parameters using a builder pattern
    # Not the most efficient, as you iterate all cell types multiple times, but way more clear what's happening
    # Normally, the amount of cell types is < O(100), so efficiency is not the biggest concern here.
    def __init__(
        self,
        netp_info=None,
        write_all_celltypes=False
    ):
        self.network_params = scp.NTParameterSet(
            data={
                "info": {},
                "network": {},
                "NMODL_mechanisms": {} # TODO
        })

        self.cell_types = []
        self.write_all_celltypes = write_all_celltypes
        self.contains_network_embedding_data = False
        self.contains_ongoing_activity_data = False
        self.contains_synapse_dynamics = False
        self.contains_evoked_activity_data = False

    def add_network_embedding(
        self,
        nr_cells_fn,
        syn_fn,
        con_fn=None
        ):
        if con_fn is None:
            logger.warning(msg="No .con filename passed. Assuming it has the same name as the .syn file...")
            con_fn = syn_fn[:-3] + "con"  # assume same name.
        nr_cells = read_cell_number_file(cell_nr_fn=nr_cells_fn)

        for anatomical_area, ct_nr_cells_map in nr_cells.items():
            for cell_type, nr_cells_this_ct in ct_nr_cells_map.items():
                if nr_cells_this_ct == 0 and not self.write_all_celltypes: continue
                cell_type_name_full = cell_type + '_' + anatomical_area
                self.network_params.network.update(
                    other=scp.NTParameterSet({
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
        self.cell_types = self.network_params.network.keys()
        return self

    def add_synapse_dynamics_generic(
        self,
        ):
        """Add synapse dynamics based on EXC/INH

        """
        if self.contains_network_embedding_data == False:
            raise ValueError("You must first add network embedding data, since that is how the connected cell types will be defined.")
        import getting_started
        syn_template_parent_dir = Path(getting_started.__file__).parent / "example_data" / "functional_constraints"
        exc_syn = scp.build_parameters(filename=syn_template_parent_dir / "exc_synapse_template.param")
        inh_syn = scp.build_parameters(filename=syn_template_parent_dir / "inh_synapse_template.param")
        for celltype_area in self.cell_types:
            celltype = "_".join(celltype_area.split("_")[:-1])
            if celltype in EXCITATORY: syn = exc_syn
            elif celltype in INHIBITORY: syn = inh_syn
            else: raise KeyError("Could not find the cell type {} in the configure excitatory or inhibitory cell types".format(celltype))
            self.network_params.network[celltype_area].update(syn)

        return self

    def add_synapse_dynamics(
        self,
        cell_type_synapse_map=None
        ):
        """

        """
        if self.contains_network_embedding_data == False:
            raise ValueError("You must first add network embedding data, since that is how the connected cell types will be defined.")
        if cell_type_synapse_map is None:
            logger.info(msg="No cell type specific synapse dynamics passed. Using synapse dynamics for generic excitatory and inhibitory instead.")
            self.add_synapse_dynamics_generic()
        else:
            assert isinstance(cell_type_synapse_map, Mapping), "If passing specific synapse dynamics per cell type, please do so as a Mapping (e.g. a dict or NTParameterSet)."
            self.network_params.network.update(other=cell_type_synapse_map)

        self.contains_synapse_dynamics = True
        return self

    def add_ongoing_activity(
        self,
        ongoing_rates_fn=None,  # TODO: default value?
        includes_anatomical_area=False,
        **kwargs
        ):
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

        Attention:
            By default, ongoing firing rates are defined per cell type, but **not** per anatomical area (in contrast to e.g. evoked activity). 
            If you want to specify ongoing activity per anatomical area, remember to set :param:`includes_anatomical_area` to ``True``.

        Attention:
            Unless specified otherwise, the ongoing firing rates will be read with a tab separator and ``index_col=0`` by default.
            First column must contain the ongoing rates. Index column must be cell types.

        See also:
            :meth:`add_evoked_activity`
        """
        if self.contains_network_embedding_data == False:
            raise ValueError("You must first add network embedding data, since that is how the connected cell types will be defined.")
        ongoing_rates = pd.read_csv(
            ongoing_rates_fn,
            sep=kwargs.pop("sep", "\t"),            # \t by default 
            index_col=kwargs.pop("index_col", 0),   # 0 by default
            **kwargs
        ).T

        for celltype_area in self.cell_types:
            celltype = "_".join(celltype_area.split("_")[:-1])
            rates_key = celltype if not includes_anatomical_area else celltype_area
            ongoing_rate = ongoing_rates[rates_key].values[0]
            self.network_params.network[celltype_area].update({
                "celltype": {
                    "spiketrain": {
                        "interval": ongoing_rate
                    }
                }
            })
        self.contains_ongoing_activity_data = True

        return self

    def add_activity(
        self,
        ct_to_activity_fn_map=None,
        key_modify_fun=None,
        additional_evoked_params=None
        ):
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
        assert isinstance(ct_to_activity_fn_map, Mapping), "Please provide a mapping between cell types and the location of their evoked activity data." 
        if self.contains_network_embedding_data == False:
            raise ValueError("You must first add network embedding data, since that is how the connected cell types will be defined.")

        assert key_modify_fun is None or callable(key_modify_fun), "If passing a value for key_modify_fun, it must be a function that takes a celltype string and returns it changed."

        for celltype_area in self.cell_types:
            celltype = "_".join(celltype_area.split("_")[:-1])
            activity_param_fn = ct_to_activity_fn_map[celltype]

            # Read PSTh data and add to netp
            activity_data_key = key_modify_fun(celltype_area) if key_modify_fun is not None else celltype_area
            if activity_data_key == None: psth = None
            else: psth = read_evoked_PSTH(fn=activity_param_fn, key=activity_data_key)
            if psth is not None: 
                self.network_params.network[celltype_area].celltype.update({
                    "pointcell": psth
                })
                if additional_evoked_params is not None:
                    self.network_params.network[celltype_area].celltype['pointcell'].update(additional_evoked_params)