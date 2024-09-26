'''
This module provides the :class:`Combiner` class and associated classes and functions.
The :class:`~biophysics_fitting.combiner.Combiner` class can be used to combine features computed by an :class:`~biophysics_fitting.evaluator.Evaluator` object.

Created on Nov 08, 2018

@author: abast
'''


class Combiner_Setup:
    """
    Setup class for the :class:`Combiner` class.
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
    This class can be used to combine features (usually) computed by an :class:`~biophysics_fitting.evaluator.Evaluator` object.
    
    For a :class:`~biophysics_fitting.simulator.Simulator` object `s`, an :class:`~biophysics_fitting.evaluator.Evaluator` object `e`, and a :class:`~biophysics_fitting.combiner.Combiner` object `c`, the typical usecase is:
    
        >>> voltage_traces_dict = s.run(params)
        >>> features = e.evaluate(voltage_traces_dict)
        >>> combined_features = c.combine(features)
            
    Internally, the Combiner iterates over all names of specified combinations. 
    Each combination is specified not only by a name of the combination, 
    but also a list of names of the features that go into that combination. 
    Each list of features is then combined by calling combinefun with that list.
    
    Example: Assume, the evaluator returns a dictionary like:
    
        >>> features = {'feature1': 1, 'feature2': 2, 'feature3': 3, 'feature4': 4}
        
    We want to combine feature 1 and 2. 
    We also want to combine features 2, 3 and 4. 
    Combining features should be done by taking the maximum.
    
    How can this be set up?
    An example, how the Combiner object can be set up can be found in :py:mod:`~biophysics_fitting.hay_complete_default_setup`
    
    Example:
    
        >>> c = Combiner()
        >>> c.setup.append('combination1', ['feature1', 'feature2'])
        >>> c.setup.append('combination2', ['feature2', 'feature3', 'feature4'])
        >>> c.setup.combinefun = max
        >>> combined_features = c.combine(features)
        >>> combined_features
        {'combination1': 2, 'combination2': 4}
    '''

    def __init__(self):
        self.setup = Combiner_Setup()

    def combine(self, features):
        '''Combines features that are computed by an Evaluator class.
        
        Details, how to set up the Combiner are in the docstring of
        the Combiner class.
        
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