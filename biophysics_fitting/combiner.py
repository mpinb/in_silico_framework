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
'''
This module provides the :py:class:`~biophysics_fitting.combiner.Combiner` class and associated classes and functions.
The :py:class:`~biophysics_fitting.combiner.Combiner` class can be used to combine features computed by an :py:class:`~biophysics_fitting.evaluator.Evaluator` object.
'''

__author__ = 'Arco Bast'
__date__ = '2018-11-08'


class Combiner_Setup:
    """
    Setup class for the :py:class:`~biophysics_fitting.combiner.Combiner` class.
    Keeps track of feature combinations and their names.
    """
    def __init__(self):
        self.combinations = []
        self.names = []
        self.combinefun = None

    def append(self, name, combination):
        """
        Appends feature names and combinations to the Combiner_Setup object.
        
        Args:
            name (str): Name of the combination
            combination (list): List of feature names that should be combined.
        """
        self.combinations.append(combination)
        self.names.append(name)


class Combiner:
    '''
    This class can be used to combine features (usually) computed by an :py:class:`~biophysics_fitting.evaluator.Evaluator` object.
    
    For a :py:class:`~biophysics_fitting.simulator.Simulator` object `s`, an :py:class:`~biophysics_fitting.evaluator.Evaluator` object `e`, and a :py:class:`~biophysics_fitting.combiner.Combiner` object `c`, the typical usecase is:
    
        >>> voltage_traces_dict = s.run(params)
        >>> features = e.evaluate(voltage_traces_dict)
        >>> combined_features = c.combine(features)
            
    Internally, the Combiner iterates over all names of specified combinations. 
    Each combination is specified not only by a name of the combination, 
    but also a list of names of the features that go into that combination. 
    Each list of features is then combined by calling combinefun with that list.
    
    Example:
    
        >>> features = {'feature1': 1, 'feature2': 2, 'feature3': 3, 'feature4': 4}
        >>> c = Combiner()
        >>> c.setup.append('combination1', ['feature1', 'feature2'])
        >>> c.setup.append('combination2', ['feature2', 'feature3', 'feature4'])
        >>> c.setup.combinefun = max
        >>> combined_features = c.combine(features)
        >>> combined_features
        {'combination1': 2, 'combination2': 4}
    
    Attributes:
        setup (:py:class:`~biophysics_fitting.combiner.Combiner_Setup`): A Combiner_Setup object that keeps track of the feature combinations.
    '''

    def __init__(self):
        self.setup = Combiner_Setup()

    def combine(self, features):
        '''Combines features that are computed by an Evaluator class.
        
        Args:
            features (list): A list of features to be combined.
            
        Returns:
            dict: A dictionary with the combined features.
        '''
        out = {}
        for n, c in zip(self.setup.names, self.setup.combinations):
            l = [features[k] for k in c]
            out[n] = self.setup.combinefun(l)
        return out
