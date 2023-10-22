'''
Created on Nov 08, 2018

@author: abast
'''


class Combiner_Setup:

    def __init__(self):
        self.combinations = []
        self.names = []
        self.combinefun = None

    def append(self, name, combination):
        self.combinations.append(combination)
        self.names.append(name)


class Combiner:
    '''This  class can be used to combine features (usually) computed by an Evaluator object.
    
    For a Simulator object s and a Evaluator object e and a Combiner object c, the typical usecase is:
    voltage_traces_dict = s.run(params)
    features = e.evaluate(voltage_traces_dict)
    combined_features = c.combine(features)
            
    Internally, the Combiner iterates over all names of specified combinations. Each combination
    is specified not only by a name of the combination, but also a list of names of the features,
    that go into that combination. Each list of features is then combined by calling combinefun with that list.
    
    Example: Assume, the evaluator returns a dictionary like:
    features = {'feature1': 1, 'feature2': 2, 'feature3': 3, 'feature4': 4}
    We want to combine feature1 and 2. We also want to combine features2, 3 and 4. Combining features should be done 
    by taking the maximum.
    
    How can this be set up?
    An example, how the Combiner object can be set up can be found in hay_complete_default_setup.    
    c = Combiner()
    c.setup.append('combination1', ['feature1', 'feature2'])
    c.setup.append('combination2', ['feature2', 'feature3', 'feature4'])
    c.setup.combinefun = max
    
    combined_features = c.combine(features)
    combined_features
    > {'combination1': 2, 'combination2': 4}
    '''

    def __init__(self):
        self.setup = Combiner_Setup()

    def combine(self, features):
        '''Combines features that are computed by an Evaluator class.
        
        Details, how to set up the Combiner are in the docstring of
        the Combiner class.   
        '''
        out = {}
        for n, c in zip(self.setup.names, self.setup.combinations):
            l = [features[k] for k in c]
            out[n] = self.setup.combinefun(l)
        return out