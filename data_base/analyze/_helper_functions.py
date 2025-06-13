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
""":skip-doc:"""

import pandas as pd
import numpy as np


def map_return_to_series(fun, *args, **kwargs):

    def inner(*args, **kwargs):
        dummy = fun(*args, **kwargs)
        return pd.Series(dict(A=dummy))

    return inner


def is_int(x):
    '''checks an object is int. surpringingly fast.'''
    try:
        int(x)
        return True
    except:
        return False


def time_list_from_pd(df):
    '''Fetch the concatenated values of all dataframe column names that can be converted to an integer.
    
    Used to parse out spike times from a :ref:`spike_times_format` dataframe and synapse activations from
    a :ref:`syn_activation_format` dataframe.
    Also filters out NaN values.
    
    Example::
    
        >>> df = pd.DataFrame({'name1': [1, 2, 3], 'name2': [4, 5, 6], '1': [7, 8, 9], '2': [10, 11, 12], '3': [13, 14, 15]})
        >>> time_list_from_pd(df)
        array([ 7,  8,  9, 10, 11, 12, 13, 14, 15])
        
    Args:
        df (:py:class:`~pandas.DataFrame`): 
            Dataframe to extract values from. Normally a :ref:`spike_times_format` or :ref:`syn_activation_format` simrun-initialized dataframe.
            
    Returns:
        :py:class:`~numpy.array`: 
            A 1D array of all values in columns that can be converted to int without NaN.
    
    '''
    relevant_columns = [_ for _ in df if is_int(_)]
    out = []
    for col in relevant_columns:
        dummy = df[col]
        dummy = dummy.dropna()
        out.append(dummy)
    return pd.concat(out).values


#def time_list_from_pd(pdf):
#    '''returns all values in columns that can be converted to int without NaN'''
#    relevant_columns = [_ for _ in pdf if is_int(_)]
#    return pd.Series(pdf[relevant_columns].values.flatten()).dropna().values


#pd_to_array = np.asarray
def pd_to_array(pdf):
    try:
        return pdf.to_numpy()
    except AttributeError:
        print('asd')
        return pdf.values  # legacy version of pandas used in in_silico_framework 2, but now deprecated


#def pd_to_array(x):
#    '''converts pd dataframe to array.
#    not very efficient ... use for small dataframes only.'''
#    if x.empty:
#        return np.array([])
#    #x = pdframe.copy()
#    array = []
#    for lv in range(max(x.index.values)+1):
#        if lv in list(x.index.values):
#            array.append(x.loc[lv])
#        else:
#            array.append([0]*len(x.iloc[0]))
#    return np.array(array)
#pdf = pd.DataFrame(np.random.random(size=(1000,1000)))
#I.np.testing.assert_equal(np.asarray(pdf),pd_to_array(pdf))