import os
from functools import partial
import pandas as pd
from simrun3.somatic_summation_model import ParseVT
import model_data_base.IO.LoaderDumper.dask_to_msgpack
dask_to_msgpack = model_data_base.IO.LoaderDumper.dask_to_msgpack
from collections import defaultdict
import single_cell_parser as scp

class CelltypeSpecificSynapticWeights:
    '''simrun3.somatic_summation_model allows specifying synaptic weights of individual synapses.
    It therefore takes a dictionarry that maps from (celltype, synapseID) to the weight of that synapse.
    
    In the default case, we assign synaptic weights per celltype, not per individual synapse. This class 
    provides a dictionary like interface, that allows to access an individual synapse
    with the tuple (celltype, synapseID) and returns the synaptic weight assigned to the celltype.
    
    It can be initialized by parsing a netowrk.param file that gets created during simulations.'''
    def __init__(self):
        self._celltype_to_syn_weight = {}

    def init_with_network_param(self, n, select_celltypes = None, use_default_weight = None):
        out = self._celltype_to_syn_weight
        for celltype in n.network:
            if select_celltypes is not None:
                if not celltype.split('_')[0] in select_celltypes:
                    print('setting weight of celltype {} to 0, as it is not within selected celltypes'.format(celltype))
                    out[celltype] = 0
                    continue
            if use_default_weight is not None:
                out[celltype] = use_default_weight
            else: #read weight
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
                    out[celltype] =  receptor.weight[0]
        print('final weights lookup dict:')
        print(out)
                
    def __getitem__(self, k):
        return self._celltype_to_syn_weight[k[0]]

def sa_to_vt_bypassing_lock(mdb_loader_dict, descriptor, classname, sa, 
                            individual_weights = False, select_celltypes = None):
    '''simulates the somatic summation model for given synapse activation. 
    The synapse activation dataframe sa may contain several simtrails.
    The PSPs matching the anatomical location are automatically loaded. For this,
    it is necessary that the model data base has been initialized with 
    model_data_base.mdb_initializers.PSPs.init'''
    parameterfiles = mdb_loader_dict['parameterfiles']()    
    out = []
    index = []
    import six
    PSP_identifiers = parameterfiles.loc[sa.index.drop_duplicates()]
    PSP_identifiers = PSP_identifiers.groupby(['neuron_param_mdbpath', 'confile']).apply(lambda x: list(x.index))
    for name, row in six.iteritems(PSP_identifiers):
        #print name
        #print ''
        #print row
        #print '*************'
        
        psp = mdb_loader_dict[descriptor, classname, name[0], name[1]]()
        pvt = ParseVT(psp, dt = 0.1, tStop=350)
        for sti in row:
            weights_dict = CelltypeSpecificSynapticWeights()
            n = parameterfiles.loc[sti]['network_param_mdbpath']
            print('loading synaptic weights from network param file ', n)
            n = scp.build_parameters(n)
            default_weight =  None if individual_weights else 1
            weights_dict.init_with_network_param(n, select_celltypes=select_celltypes,
                                 use_default_weight = default_weight)
            
            index.append(sti)
            t,v = pvt.parse_sa(sa.loc[sti], weights=weights_dict)
            out.append(v)
    out_pdf = pd.DataFrame(out, index = index, columns = t).sort_index()
    return out_pdf

def get_mdb_loader_dict(mdb, descriptor = None, PSPClass_name = None):
    from model_data_base.IO.LoaderDumper import load
    import six
    keys = [k for k in list(mdb['PSPs'].keys()) if (k[1] == PSPClass_name) and (k[0] == descriptor)]
    keys = keys + ['parameterfiles']
    mdb_loader_dict = {k: mdb['PSPs']._sql_backend[k].relpath for k in keys}
    mdb_loader_dict = {k: partial(load, os.path.join(mdb['PSPs'].basedir, v)) 
                       for k,v in six.iteritems(mdb_loader_dict)}   
    return mdb_loader_dict

import barrel_cortex
class DistributedDDFWithSaveMethod:
    def __init__(self, mdb = None, key = None, ddf = None, dumper = None, get = None):
        self.ddf = ddf
        self._mdb = mdb
        self._key = key
        self._dumper = dumper
        self._get = get
    
    def save(self):
        self._mdb.setitem(self._key, self.ddf, dumper = self._dumper, get = self._get)
        
def init(mdb, description_key = None, PSPClass_name = None, client = None, block_till_saved = False, 
         persistent_df = True, individual_weights = False, select_celltypes = None):
    mdb_loader_dict = get_mdb_loader_dict(mdb, description_key, PSPClass_name)
    part = partial(sa_to_vt_bypassing_lock, mdb_loader_dict, description_key, PSPClass_name, 
                   individual_weights = individual_weights, select_celltypes = select_celltypes)
    if individual_weights:
        description_key = description_key + '_individual_weights'
    if select_celltypes is not None:
        if select_celltypes == barrel_cortex.excitatory:
            suffix = 'EXC'
        elif select_celltypes == barrel_cortex.inhibitory:
            suffix = 'INH'
        else:
            suffix = '_'.join(sorted(select_celltypes))
        description_key += suffix
    sa = mdb['synapse_activation']
    if persistent_df:
        sa = client.persist(sa)
    meta = part(sa.get_partition(0).compute())
    vt_new = sa.map_partitions(part, meta = meta)
    if persistent_df:
        vt_new = client.persist(vt_new)  
    mdb_vt = mdb.create_sub_mdb('voltage_traces_somatic_summation_model', raise_ = False)
    if block_till_saved:
        mdb_vt.setitem((description_key, PSPClass_name), vt_new, 
                       dumper = dask_to_msgpack, get = client.get)
    else:
        return DistributedDDFWithSaveMethod(mdb = mdb_vt, 
                                            key = (description_key, PSPClass_name),
                                            ddf = vt_new,
                                            dumper = dask_to_msgpack, 
                                            get = client.get)