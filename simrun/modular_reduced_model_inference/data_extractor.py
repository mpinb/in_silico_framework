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

"""Extract and parse data from databases.

Data extractors initialize from ReducedModel objects.
Depending on the reduced model object, the data extractors fetch data from the database and return it in a structured way.
These data extractors are specific to match a :py:class:`simrun.modular_reduced_model_inference.Strategy` object.
For example, the spatiotemporal raised cosine strategy requires to bin the synapse activations spatiotemporally.
This is then handled with the :py:class:`DataExtractor_spatiotemporalSynapseActivation` class.
"""


import numpy
import pandas as pd
from data_base.analyze.spike_detection import spike_in_interval
from data_base.IO.LoaderDumper import pandas_to_parquet
from config.isf_logging import logger

class _DataExtractor(object):
    """Simple base class for data extractors.
    
    Child classes must implement ``get`` and ``setup`` methods.
    """
    def get(self):
        """:skip-doc:"""
        pass

    def setup(self, Rm):
        """Setup necessary parameters, depending on which RM is passed
        
        Args:
            Rm (:py:class:`Rm`): Reduced model object
        """        
        pass


class DataExtractor_spatiotemporalSynapseActivation(_DataExtractor):
    '''Extracts matrix of the shape ``(trial, time, space)`` from spatiotemporal synapse activation binning
    
    Attributes:
        key (tuple|str): key to access the data in the :py:class:`DataBase`
        data (dict): dictionary with groups as keys and spatiotemporal inputpatterns as keys.
    '''

    def __init__(self, key):
        """
        Args:
            key (tuple|str): key to access the data in the :py:class:`DataBase`
        """
        self.key = key
        self.data = None

    def setup(self, Rm):
        """Set up the data extractor.
        
        This method sets up the time window and selected trials for fetching the
        synaptse input data.
        
        Args:
            Rm (:py:class:`Rm`): Reduced model object. Must have the atttributes ``db``, ``tmin``, ``tmax``, ``width``, and ``selected_indices``.
        """
        self.db = Rm.db
        self.tmin = Rm.tmin
        self.tmax = Rm.tmax
        self.width = Rm.width
        self.selected_indices = Rm.selected_indices
        self.data = {
            g: self._get_spatiotemporal_input(g) for g in self.get_groups()
        }

    @staticmethod
    def _get_spatial_bin_level(key):
        '''Get the string index of the database key that relects the spatial dimension
        
        Args:
            key (tuple): key to access the data in the :py:class:`DataBase`
            
        Returns:
            int: index of the spatial dimension in the key
            
        Example:

            >>> key = ('sub_database', 'spatiotemporal_synapse_activation__binned_somadist__100to150__group1')
            >>> _get_spatial_bin_level(key)
            1
        '''
        # TODO: shouldnt this be +1? The level comes AFTER the binned_somadist part
        return key[-1].split('__').index('binned_somadist')

    def get_spatial_binsize(self):
        '''Get the spatial binsize
        
        Fetches the spatial bin size from a grouped synapse activation dataframe based on the database key.
        
        Returns:
            float: spatial binsize, indicating how much :math:`\mu m` it covers.
        '''
        db = self.db[0] if type(db) == list else self.db
        key = self.key
        level = self._get_spatial_bin_level(key)
        spatial_binsize = db[key].keys()[0][level]  # something like '100to150'
        spatial_binsize = spatial_binsize.split('to')
        spatial_binsize = float(spatial_binsize[1]) - float(spatial_binsize[0])
        return spatial_binsize

    def get_groups(self):
        '''Get all groups (other than spatial binning)
        
        Returns:
            set: Set of groups that define how the synapse activations are grouped.
        '''
        db = self.db
        if type(db) != list:
            db = [db]
        key = self.key
        level = self._get_spatial_bin_level(key)
        out = []
        for single_db in db:
            for k in single_db[key].keys():
                k = list(k)
                k.pop(level)
                out.append(tuple(k))
        return set(out)

    def get_sorted_keys_by_group(self, group, db=None):
        '''returns keys sorted such that the first key is the closest to the soma
        
        '''
        if db == None:
            db = self.db
        db = db[0] if type(db) == list else db
        key = self.key
        group = list(group)
        level = self._get_spatial_bin_level(key)
        keys = db[key].keys()
        keys = sorted(keys, key=lambda x: float(x[level].split('to')[0]))
        out = []
        for k in keys:
            k_copy = list(k[:])
            k_copy.pop(level)
            if k_copy == group:
                out.append(k)
        return out

    def _get_spatiotemporal_input(self, group):
        '''returns spatiotemporal input in the following dimensions:
        (trial, time, space)'''
        db = self.db
        if type(db) != list:
            db = [db]
        key = self.key
        #         keys = self.get_sorted_keys_by_group(group)
        #         out = [db[key][k][:,self.tmax-self.width:self.tmax] for k in keys]
        #         out = numpy.dstack(out)

        outs = []
        for m, single_db in enumerate(db):
            keys = self.get_sorted_keys_by_group(group, db=single_db)
            if self.selected_indices is not None:
                out = [
                    single_db[key][k][self.selected_indices[m], self.tmax - self.width:self.tmax]
                    for k in keys
                ]
            else:
                out = [
                    single_db[key][k][:, self.tmax - self.width:self.tmax]
                    for k in keys
                ]
            out = numpy.dstack(out)
            outs.append(out)

        outs = numpy.concatenate(outs, axis=0)
        logger.info(outs.shape)
        return outs

    def get(self):
        '''Get the spatiotemporal input patterns.
        
        Example:
        
            >>> data = de.get()
            >>> data.keys()
            ['group1', 'group2']
            >>> data['group1'].shape
            (n_trials, n_time, n_space)
        
        Returns:
            dict: dictionary with groups as keys and spatiotemporal inputpatterns as keys.        
        '''
        return self.data  # {g: self.get_spatiotemporal_input(g) for g in self.get_groups()}


class DataExtractor_categorizedTemporalSynapseActivation(_DataExtractor):
    """:skip-doc:"""
    def __init__(self, key):
        self.key = key
        self.data = None

    def setup(self, Rm):
        self.db = Rm.db
        self.tmin = Rm.tmin
        self.tmax = Rm.tmax
        self.width = Rm.width
        self.selected_indices = Rm.selected_indices
        self._set_data()

    def _set_data(self):
        dbs = self.db
        if type(dbs) != list:
            dbs = [dbs]
        key = self.key
        keys = dbs[0][key].keys()
        out = {}
        outs = []
        for k in keys:
            out[k] = []
            for m in dbs:
                #print set(m[key].keys())
                #print keys
                assert set(m[key].keys()) == set(keys)
                if self.selected_indices is None:
                    out[k].append(m[key][k][:, self.tmax - self.width:self.tmax])
                else:
                    out[k].append(m[key][k][self.selected_indices, self.tmax - self.width:self.tmax])
            out[k] = numpy.vstack(out[k])
        self.data = out

    def get(self):
        return self.data


class DataExtractor_spiketimes(_DataExtractor):
    """:skip-doc:"""
    def setup(self, Rm):
        self.db = Rm.db
        self.st = None
        self.selected_indices = Rm.selected_indices

    def get(self):
        if type(self.db) != list:
            return self.db['spike_times']
        else:
            st_list = []
            if self.selected_indices is not None:
                for m, single_db in enumerate(self.db):
                    st_list.append(single_db['spike_times'].iloc[self.selected_indices[m]])
            else:
                for single_db in self.db:
                    st_list.append(single_db['spike_times'])
            return pd.concat(st_list)


class DataExtractor_object(_DataExtractor):
    """:skip-doc:"""
    def __init__(self, key):
        self.key = key

    def setup(self, Rm):
        self.db = Rm.db
        self.data = Rm[self.key]  #rieketodo

    def get(self):
        return self.data


class DataExtractor_spikeInInterval(_DataExtractor):
    """:skip-doc:"""
    def __init__(self, tmin=None, tmax=None):
        self.tmin = tmin
        self.tmax = tmax

    def setup(self, Rm):
        if self.tmin is None:
            self.tmin = Rm.tmin
        if self.tmax is None:
            self.tmax = Rm.tmax
        self.db = Rm.db
        self.selected_indices = Rm.selected_indices

        if type(self.db) != list:
            st = self.db['spike_times']
        else:
            st_list = []
            if self.selected_indices is not None:
                for m, single_db in enumerate(self.db):
                    st_list.append(single_db['spike_times'].iloc[
                        self.selected_indices[m]])
            else:
                for single_db in self.db:
                    st_list.append(single_db['spike_times'])
            st = pd.concat(st_list)

        self.sii = spike_in_interval(st, tmin=self.tmin, tmax=self.tmax)

    def get(self):
        return self.sii


class DataExtractor_ISI(_DataExtractor):
    """:skip-doc:"""
    def __init__(self, t=None):
        self.t = t

    def setup(self, Rm):
        self.db = Rm.db
        if self.t is None:
            self.t = Rm.tmin
        self.selected_indices = Rm.selected_indices

        if type(self.db) != list:
            st = self.db['spike_times']
        else:
            st_list = []
            if self.selected_indices is not None:
                for m, single_db in enumerate(self.db):
                    st_list.append(single_db['spike_times'].iloc[
                        self.selected_indices[m]])
            else:
                for single_db in self.db:
                    st_list.append(single_db['spike_times'])
            st = pd.concat(st_list)

        t = self.t
        st[st > t] = numpy.NaN
        self.ISI = st.max(axis=1) - t

    def get(self):
        return self.ISI


class DataExtractor_daskDataframeColumn(_DataExtractor):  #rieketodo
    """:skip-doc:"""
    def __init__(self, key, column, client=None):
        if not isinstance(key, tuple):
            self.key = (key,)
        else:
            self.key = key
        self.column = column
        self.client = client
        self.data = None

    def setup(self, Rm):
        self.db = Rm.db
        cache = self.db.create_sub_db(
            'DataExtractor_daskDataframeColumn_cache', raise_=False)
        complete_key = list(self.key) + [self.column]
        complete_key = map(str, complete_key)
        complete_key = tuple(complete_key)
        print(complete_key)
        if not complete_key in cache.keys():
            slice_ = self.db[self.key][self.column]
            slice_ = self.client.compute(slice_).result()
            cache.setitem(
                complete_key,
                slice_,
                dumper=pandas_to_parquet)
        self.data = cache[complete_key]
        # after the setup, the object must be serializable and therefore must not contain a client objectz
        self.client = None

    def get(self):
        return self.data
