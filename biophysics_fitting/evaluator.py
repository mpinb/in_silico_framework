'''
Created on Nov 08, 2018

@author: abast
'''

class Evaluator_Setup:
    def __init__(self):
        self.pre_funs = []
        self.evaluate_funs = []
        self.finalize_funs = []

class Evaluator:
    def __init__(self):
        '''This  class can be used to extract features from (usually) voltagetraces
        of different stimuli. The voltage traces are (usually) computed with a Simulator 
        object by calling its run method.
        
        In an optimization the features returned by Evaluator.evaluate are saved together
        with to corresponding parameter values.

        Note: Combining features to reduce the number of objectives should be done with the Combiner object.        
        
        For a Simulator object s and a Evaluator object e, the typical usecase is:
        voltage_traces_dict = s.run(params)
        features = e.evaluate(voltage_traces_dict)
                
        The "program flow" in the Evaluator can be split in two parts:
        (1) for each key in the voltage_traces_dict: 
            ---> apply evaluate_fun, that is registered with a name that matches the key.
                    Extracts features from the voltage trace.
        (2) perform arbitrary operations on the resulting dictionary 
                (e.g. merge it from a nested to a flat dictionary or compute more complex features
                by combineing features from different stimuli)
                
        
        How can the Evaluator be set up?
        An example, how the Evaluator object can be set up can be found in hay_complete_default_setup.
        
        e = Evaluator()
        e.setup.evaluate_funs.append([in_name, evaluate_fun, out_name]) # corresponds to step (1)
        e.setup.finalize_funs.append(finalize_fun) # corresponds to step (2)
        
        What form do the functions need to have?
        def examplary_evaluate_fun(**kwargs):
            # kwargs are keys and values of voltage_traces_dict[in_name]
            # extract features from kwargs
            return out_dict # keys are names of features, values are features

        def finalize_fun(dict_):
            # dict_ is a dictionary with out_name of the evaluate_funs as keys.
            # and the returned dictionary out_dict as values, 
            # i.e. out_dict is a nested dictionary.
            # dict_ can now be arbitrarily modified, e.g. flattened.
            return modified_dict
        '''
        #self.objectives = objectives
        self.setup = Evaluator_Setup()
        
    def evaluate(self, features_dict, raise_ = True):
        '''Extracts features from a simulation result computed by Simulator.run()
        
        Details, how to set up the Evaluator are in the docstring of
        the Evaluator class.
        
        raise_: if True will raise an error if the required voltage trace is not in features_dict. if False,
        will not raise an error, and evaluate all features that can be evaluated given the provided features_dict.'''        
        ret = {}
        for fun in self.setup.pre_funs:
            features_dict = fun(features_dict)
        for in_name, fun, out_name in self.setup.evaluate_funs:
            if not raise_:
                if not in_name in features_dict:
                    continue
            ret[out_name] = fun(**features_dict[in_name])
        for fun in self.setup.finalize_funs:
            ret = fun(ret)
        return ret