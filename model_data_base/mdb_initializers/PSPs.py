import os
import single_cell_parser as scp
from model_data_base.mdbopen import create_mdb_path, resolve_mdb_path
from model_data_base.IO.LoaderDumper import pandas_to_msgpack


def get_confile_form_network_param(n):
    confile = set(
        [n.network[k].synapses.connectionFile for k in list(n.network.keys())])
    synfile = set([
        n.network[k].synapses.distributionFile for k in list(n.network.keys())
    ])
    assert len(confile) == 1
    assert len(synfile) == 1
    assert list(confile)[0][:-4] == list(synfile)[0][:-4]
    return list(confile)[0]


def get_parameterfiles_df_with_confile_and_neuron_param_path(mdb):
    parameterfiles = mdb['parameterfiles']
    f = mdb['parameterfiles_network_folder']
    map_to_confilepath = {}
    for ff in os.listdir(f):
        if ff == 'Loader.pickle':
            continue
        n = scp.build_parameters(os.path.join(f, ff))
        map_to_confilepath[ff] = get_confile_form_network_param(n)
    import six
    parameterfiles['confile'] = parameterfiles.hash_network.map(
        map_to_confilepath)
    map_to_parampath = {
        v: create_mdb_path(os.path.join(mdb['parameterfiles_cell_folder'], v))
        for k, v, in six.iteritems(parameterfiles.hash_neuron.drop_duplicates())
    }
    parameterfiles['neuron_param_mdbpath'] = parameterfiles['hash_neuron'].map(
        map_to_parampath)
    map_to_parampath = {
        v:
            create_mdb_path(
                os.path.join(mdb['parameterfiles_network_folder'], v)) for k, v,
        in six.iteritems(parameterfiles.hash_network.drop_duplicates())
    }
    parameterfiles['network_param_mdbpath'] = parameterfiles[
        'hash_network'].map(map_to_parampath)
    return parameterfiles


def get_PSP_determinants_from_mdb(mdb):
    '''returns the combinations of neuron_parameters and network embeddings for which 
    PSPs need to be computed for somatic summation model'''
    parameterfiles = get_parameterfiles_df_with_confile_and_neuron_param_path(
        mdb)
    return parameterfiles[['confile', 'neuron_param_mdbpath'
                          ]].drop_duplicates().reset_index(drop=True)


def init(mdb,
         client=None,
         description_key=None,
         PSPClass=None,
         PSPClass_kwargs={}):
    '''This calculates PSPs for a model_data_base, that has been initialized with
    I.mdb_init_simrun_general. It determines all network embeddings (confile) and neuron models (neuron_param)
    present in the database and initializes the PSPs computation accordingly.
        
    The PSPs are calculated using PSPClass. This can e.g. be a class defined in simrun3.PSP_with_modification.
    This class will be initialized as follows for all neuron_param and confile:
    psp_class_instance = PSPClass(neuron_param, confile, **PSPClass_kwargs)
        
    PSPClass needs to provide a get method, that returns a PSPs object, as defined in simrun3.synaptic_strength_fitting.
    The PSPs object will be executed and saved to mdb under the following location:
    mdb['PSPs']['description_key', PSPClass.__name__, 'neuron_param_path', 'confile_path']'''
    pdf = get_PSP_determinants_from_mdb(mdb)
    pspmdb = mdb.create_sub_mdb('PSPs', raise_=False)
    pspmdb.setitem(
        'parameterfiles',
        get_parameterfiles_df_with_confile_and_neuron_param_path(mdb),
        dumper=pandas_to_msgpack)
    psps_out = []
    keys_out = []
    for index, row in pdf.iterrows():
        print('setting up computation of PSPs for network embedding ', row.confile, \
                    ' and biophysical model ', row.neuron_param_mdbpath)
        print('corresponding to ', resolve_mdb_path(row.confile), \
                    resolve_mdb_path(row.neuron_param_mdbpath))
        neuron_param = resolve_mdb_path(row.neuron_param_mdbpath)
        psp = PSPClass(scp.build_parameters(neuron_param), row.confile,
                       **PSPClass_kwargs)
        psp = psp.get()
        psp.run(client)
        psps_out.append(psp)
        keys_out.append((description_key, PSPClass.__name__,
                         row.neuron_param_mdbpath, row.confile))
    for k, p in zip(keys_out, psps_out):
        vt = p.get_voltage_and_timing()  # waits till computation is finished
        pspmdb[k] = p
