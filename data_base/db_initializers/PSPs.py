# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.
"""
I think this is used for the somatic summation model?
I currently leave this undocumented until I (or someone else) can properly document this.
- Bjorge 2024-11-12

:skip-doc:
"""

import os
import single_cell_parser as scp
from data_base.dbopen import create_modular_db_path, resolve_db_path
from data_base.IO.LoaderDumper import pandas_to_msgpack
# from data_base.isf_data_base.IO.LoaderDumper import pandas_to_parquet


def get_confile_form_network_param(n):
    """Fetch the :ref:`con_file_format` file from a network parameters object.
    
    Args:
        n (:py:class:`~single_cell_parser.network_parameters.NetworkParameters`): The network parameters object.
        
    See also:
        The :ref:`network_parameters_format` format.
    """
    confile = set(
        [n.network[k].synapses.connectionFile for k in list(n.network.keys())])
    synfile = set([
        n.network[k].synapses.distributionFile for k in list(n.network.keys())
    ])
    assert len(confile) == 1
    assert len(synfile) == 1
    assert list(confile)[0][:-4] == list(synfile)[0][:-4]
    return list(confile)[0]


def get_parameterfiles_df_with_confile_and_neuron_param_path(db):
    """Parse the parameterfiles database and add the ``confile`` and ``neuron_param_dbpath`` columns.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): The database object.
        
    Returns:
        :py:class:`pandas.DataFrame`: The parameterfiles dataframe with the additional columns ``confile`` and ``neuron_param_db``
    """
    parameterfiles = db['parameterfiles']
    f = db['parameterfiles_network_folder']
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
        v: create_modular_db_path(os.path.join(db['parameterfiles_cell_folder'], v))
        for k, v, in six.iteritems(parameterfiles.hash_neuron.drop_duplicates())
    }
    parameterfiles['neuron_param_dbpath'] = parameterfiles['hash_neuron'].map(
        map_to_parampath)
    map_to_parampath = {
        v:
            create_modular_db_path(
                os.path.join(db['parameterfiles_network_folder'], v)) for k, v,
        in six.iteritems(parameterfiles.hash_network.drop_duplicates())
    }
    parameterfiles['network_param_dbpath'] = parameterfiles[
        'hash_network'].map(map_to_parampath)
    return parameterfiles


def get_PSP_determinants_from_db(db):
    '''Get the combinations of :ref:`cell_parameters_format` files and network embeddings for which 
    PSPs need to be computed
    
    For a given somatic summation model, the PSPs are computed for all combinations of
    network embeddings and neuron models present in the simrun-initialized database.
    
    Args:
        db (:py:class:`~data_base.isf_data_base.isf_data_base.ISFDataBase`): 
            The simrun-initialized database object.
            
    Returns:
        :py:class:`pandas.DataFrame`: The dataframe with the columns ``confile`` and ``neuron_param_dbpath``.
        
    See also:
        :py:meth:`~data_base.db_initializers.load_simrun_general.init`
        for initializing a database with :py:mod:`simrun` data.    
    '''
    parameterfiles = get_parameterfiles_df_with_confile_and_neuron_param_path(
        db)
    return parameterfiles[['confile', 'neuron_param_dbpath']].drop_duplicates().reset_index(drop=True)


def init(
    db,
    client=None,
    description_key=None,
    PSPClass=None,
    PSPClass_kwargs={}):
    '''Calculate the PSPs for all network embeddings and neuron models present in the simrun-initialized database.
    
    The PSPs are calculated using :paramref:`PSPClass`. 
    This can e.g. be a class defined in :py:mod:`~simrun.PSP_with_modification`.
    This class will be initialized as follows for all neuron_param and confile::
    
        >>> psp_class_instance = PSPClass(neuron_param, confile, **PSPClass_kwargs)
        
    :paramref:`PSPClass` needs to provide a ``get`` method that returns a :py:class:`~simrun.synaptic_strength_fitting.PSPs` object, 
    The :py:class:`~simrun.synaptic_strength_fitting.PSPs` object is executed and saved to :paramref:`db` under the following key::
    
        >>> db['PSPs']['description_key', PSPClass.__name__, 'neuron_param_path', 'confile_path']
    
    See also:
        :py:meth:`~data_base.db_initializers.load_simrun_general.init`
        for initializing a database with :py:mod:`simrun` data.
    '''
    pdf = get_PSP_determinants_from_db(db)
    pspdb = db.create_sub_db('PSPs', raise_=False)
    pspdb.set(
        'parameterfiles',
        get_parameterfiles_df_with_confile_and_neuron_param_path(db),
        dumper=pandas_to_msgpack)
    psps_out = []
    keys_out = []
    for index, row in pdf.iterrows():
        print('setting up computation of PSPs for network embedding ', row.confile, \
                    ' and biophysical model ', row.neuron_param_dbpath)
        print('corresponding to ', resolve_db_path(row.confile), \
                    resolve_db_path(row.neuron_param_dbpath))
        neuron_param = resolve_db_path(row.neuron_param_dbpath)
        psp = PSPClass(scp.build_parameters(neuron_param), row.confile,
                       **PSPClass_kwargs)
        psp = psp.get()
        psp.run(client)
        psps_out.append(psp)
        keys_out.append((description_key, PSPClass.__name__,
                         row.neuron_param_dbpath, row.confile))
    for k, p in zip(keys_out, psps_out):
        vt = p.get_voltage_and_timing()  # waits till computation is finished
        pspdb[k] = p
