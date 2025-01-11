"""
The somatic summation model is - I believe - the "synchronous proximal drive" model as used in the L6 paper.
The reduced model is a more general extension of this, I believe.
As of now, i don't see the need (and may lack the capacity) to document this.
- Bjorge, 2024-11-12

:skip-doc:
"""

import os
from functools import partial
import pandas as pd
from simrun.somatic_summation_model import ParseVT
from ..IO.LoaderDumper import dask_to_parquet
from config.cell_types import EXCITATORY, INHIBITORY
# dask_to_parquet = data_base.IO.LoaderDumper.dask_to_parquet
from collections import defaultdict
import single_cell_parser as scp


class CelltypeSpecificSynapticWeights:
    '''Configure cell type specific synaptic weights for the somatic summation model.
    
    :py:mod:`simrun.somatic_summation_model` allows specifying synaptic weights of individual synapses.
    For this, it needs a dictionary that maps from (celltype, synapseID) to the weight of that synapse. 
    This class parses a :ref:`network_parameters_format` file and extracts the synaptic weights of individual synapses.
    These can then be accessed in a dictionary-like fashion for use in :py:mod:`~simrun.somatic_summation_model`::
    
        >>> n = scp.build_parameters('path/to/network.param')
        >>> weights = CelltypeSpecificSynapticWeights()
        >>> weights.init_with_network_param(n)
        >>> celltype, synapseID = 'L23_PC', 0
        >>> weights[(celltype, synapseID)]
    
    Attributes:
        _celltype_to_syn_weight (dict): The dictionary that maps from (celltype, synapseID) to the weight of that synapse.
        
    versionadded:: 0.1.0
        Cell type specific synaptic weights are supported, but **not** synapse-specific weights (yet).
        The synapse ID is ignored.
    '''

    def __init__(self):
        self._celltype_to_syn_weight = {}

    def init_with_network_param(
        self,
        n,
        select_celltypes=None,
        use_default_weight=None):
        """Initialize the synaptic weights with :ref:`network_parameters_format`.
        
        Args:
            n (:py:class:`~sumatra.parameters.NTParameterSet`): The network parameters object.
            select_celltypes (list): If not None, only the synaptic weights of the celltypes in this list are loaded.
            use_default_weight (float): If not None, all synaptic weights are set to this value.
        
        Raises:
            NotImplementedError: If the network parameters object contains synapses with more than one receptor.
            NotImplementedError: If the network parameters object contains synapses with a receptor that is not 'glutamate_syn' or 'gaba_syn'.
        """
        out = self._celltype_to_syn_weight
        for celltype in n.network:
            if select_celltypes is not None:
                if not celltype.split('_')[0] in select_celltypes:
                    print(
                        'setting weight of celltype {} to 0, as it is not within selected celltypes'
                        .format(celltype))
                    out[celltype] = 0
                    continue
            if use_default_weight is not None:
                out[celltype] = use_default_weight
            else:  #read weight
                #confile = n.network[celltype].synapses.connectionFile
                #cellNr = n.network[celltype].cellNr
                receptors = n.network[celltype].synapses.receptors
                if len(receptors) > 1:
                    raise NotImplementedError()
                receptor_key = list(receptors.keys())[0]
                receptor = receptors[receptor_key]
                if receptor_key not in ['glutamate_syn', 'gaba_syn']:
                    raise NotImplementedError()
                if receptor_key == 'gaba_syn':
                    out[celltype] = receptor.weight
                elif receptor_key == 'glutamate_syn':
                    if not receptor.weight[0] == receptor.weight[1]:
                        raise NotImplementedError()
                    out[celltype] = receptor.weight[0]
        print('final weights lookup dict:')
        print(out)

    def __getitem__(self, k):
        """
        
        Attention:
            This method returns the weight of synapse ID 0 for the given celltype.
            It thus only supports cell type specific synaptic weights, not synapse-specific weights.
        """
        return self._celltype_to_syn_weight[k[0]]


def sa_to_vt_bypassing_lock(
    db_loader_dict,
    descriptor,
    classname,
    sa,
    individual_weights=False,
    select_celltypes=None):
    '''
    
    
    simulates the somatic summation model for given synapse activation. 
    The synapse activation dataframe sa may contain several simtrials.
    
    The PSPs matching the anatomical location are automatically loaded. For this,
    it is necessary that the model data base has been initialized with 
    data_base.db_initializers.PSPs.init
    
    
    '''
    # parse parameterfiles from simrun-initialized database
    parameterfiles = db_loader_dict['parameterfiles']()
    out = []
    index = []
    import six
    PSP_identifiers = parameterfiles.loc[sa.index.drop_duplicates()]
    PSP_identifiers = PSP_identifiers.groupby(['neuron_param_dbpath', 'confile']).apply(lambda x: list(x.index))
    
    # iterate over all PSPs and compute the voltage traces
    for name, row in six.iteritems(PSP_identifiers):
        psp = db_loader_dict[descriptor, classname, name[0], name[1]]()
        pvt = ParseVT(psp, dt=0.1, tStop=350)
        for sti in row:
            weights_dict = CelltypeSpecificSynapticWeights()
            n = parameterfiles.loc[sti]['network_param_dbpath']
            print('loading synaptic weights from network param file ', n)
            n = scp.build_parameters(n)
            default_weight = None if individual_weights else 1
            weights_dict.init_with_network_param(
                n,
                select_celltypes=select_celltypes,
                use_default_weight=default_weight)

            index.append(sti)
            t, v = pvt.parse_sa(sa.loc[sti], weights=weights_dict)
            out.append(v)
    out_pdf = pd.DataFrame(out, index=index, columns=t).sort_index()
    return out_pdf


def get_db_loader_dict(db, descriptor=None, PSPClass_name=None):
    """Get the loader functions for the PSPs from the database.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): The simrun-initialized database object.
        descriptor (str): The descriptor of the PSPs.
        PSPClass_name (str): The name of the PSP class.
        
    Returns:
        dict: A dictionary that maps from the keys of the PSPs to the loader functions.
    """
    from data_base.isf_data_base.IO.LoaderDumper import load
    import six
    keys = [
        k for k in list(db['PSPs'].keys())
        if (k[1] == PSPClass_name) and (k[0] == descriptor)
    ]
    keys = keys + ['parameterfiles']
    db_loader_dict = {k: db['PSPs']._sql_backend[k].relpath for k in keys}
    db_loader_dict = {
        k: partial(load, os.path.join(db['PSPs'].basedir, v))
        for k, v in six.iteritems(db_loader_dict)
    }
    return db_loader_dict


class DistributedDDFWithSaveMethod:

    def __init__(self, db=None, key=None, ddf=None, dumper=None, scheduler=None):
        self.ddf = ddf
        self._db = db
        self._key = key
        self._dumper = dumper
        self._get = get

    def save(self):
        self._db.set(
            self._key,
            self.ddf,
            dumper=self._dumper,
            get=self._get)


def init(
    db,
    description_key=None,
    PSPClass_name=None,
    client=None,
    block_till_saved=False,
    persistent_df=True,
    individual_weights=False,
    select_celltypes=None):
    db_loader_dict = get_db_loader_dict(db, description_key, PSPClass_name)
    part = partial(sa_to_vt_bypassing_lock,
                   db_loader_dict,
                   description_key,
                   PSPClass_name,
                   individual_weights=individual_weights,
                   select_celltypes=select_celltypes)
    if individual_weights:
        description_key = description_key + '_individual_weights'
    if select_celltypes is not None:
        if sorted(select_celltypes) == sorted(EXCITATORY):
            suffix = 'EXC'
        elif sorted(select_celltypes) == sorted(INHIBITORY):
            suffix = 'INH'
        else:
            suffix = '_'.join(sorted(select_celltypes))
        description_key += suffix
    sa = db['synapse_activation']
    if persistent_df:
        sa = client.persist(sa)
    meta = part(sa.get_partition(0).compute())
    vt_new = sa.map_partitions(part, meta=meta)
    if persistent_df:
        vt_new = client.persist(vt_new)
    db_vt = db.create_sub_db('voltage_traces_somatic_summation_model',
                                raise_=False)
    if block_till_saved:
        db_vt.set(
            (description_key, PSPClass_name),
            vt_new,
            dumper=dask_to_parquet,
            scheduler=client)
    else:
        return DistributedDDFWithSaveMethod(
            db=db_vt,
            key=(description_key, PSPClass_name),
            ddf=vt_new,
            dumper=dask_to_parquet,
            scheduler=client)
