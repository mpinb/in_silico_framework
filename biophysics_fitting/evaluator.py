'''Extract features from voltage traces.
'''
__author__ = "Arco Bast"
__date__ = "2018-11-08"


class Evaluator_Setup:
    '''Setup for an :py:class:`~Evaluator` object
    
    This class is an attribute of the :py:class:`~Evaluator` class, and should only veer be accessed via the :py:class:`~Evaluator` object.
    It takes care of applying evaluation functions to voltage traces, and finalizing the results.
    
    Attributes:
        pre_funs (list): 
            A list of functions to be applied to the input dictionary before the evaluation functions are applied.
        evaluate_funs (list): 
            A list of functions to be applied to the voltage traces. Each element of the list is a list of three elements: 
            the name of the input voltage trace, the function to be applied to the voltage trace, and the name of the output feature.
        finalize_funs (list): 
            A list of functions to be applied to the output of the evaluation functions. The output of the last function in this list is the output of the :meth:`~Evaluator.evaluate` method.
    '''
    
    def __init__(self):
        self.pre_funs = []
        self.evaluate_funs = []
        self.finalize_funs = []


class Evaluator:
    '''Extract features from voltage traces.
    
    This  class can be used to extract features from (usually) voltage traces
    of different stimuli. The voltage traces are (usually) computed with a Simulator 
    object by calling its run method.
    
    In an optimization the features returned by Evaluator.evaluate are saved together
    with to corresponding parameter values.
    
    For a Simulator object s and a Evaluator object e, the typical usecase is::
    
    >>> voltage_traces_dict = s.run(params)
    >>> features = e.evaluate(voltage_traces_dict)
            
    The workflow in the Evaluator can be split in two parts:
    
    1. Apply an ``evaluate_fun`` on each matching key in :paramref:`voltage_traces_dict` 
        These extract features from the voltage trace. 
        These functions are registered under :py:attr:`Evaluator_Setup.evaluate_funs`.
    2. Perform arbitrary operations on the resulting dictionary 
        (e.g. merge it from a nested to a flat dictionary or compute more complex features
        by combineing features from different stimuli)
            
    An example set up can be found in :py:meth:`~biophysics_fitting.hay_complete_default_setup.get_Evaluator`.
    
    
    Example: 
        
        >>> def examplary_evaluate_fun(**kwargs):
        >>>    # kwargs are keys and values of voltage_traces_dict[in_name]
        >>>    # extract features from kwargs
        >>>    return out_dict # keys are names of features, values are features

        >>> def finalize_fun(dict_):
        >>>    # dict_ is a dictionary with out_name of the evaluate_funs as keys.
        >>>    # and the returned dictionary out_dict as values, 
        >>>    # i.e. out_dict is a nested dictionary.
        >>>    # dict_ can now be arbitrarily modified, e.g. flattened.
        >>>    return modified_dict

        >>> e = Evaluator()
        >>> e.setup.evaluate_funs.append([in_name, evaluate_fun, out_name])  # corresponds to step (1)
        >>> e.setup.finalize_funs.append(finalize_fun)  # corresponds to step (2)

    Note: 
        Combining features to reduce the number of objectives should be done with the :py:class:`~biophysics_fitting.combiner.Combiner` object.        
    
    Attributes:
        setup (:py:class:`~biophysics_fitting.evaluator.Evaluator_Setup`): 
            A Evaluator_Setup object that keeps track of the evaluation functions.
    '''
    def __init__(self):
        #self.objectives = objectives
        self.setup = Evaluator_Setup()

    def evaluate(self, features_dict, raise_=True):
        '''Extracts features from a simulation result computed by :py:meth:`biophysics_fitting.simulator.Simulator.run`
        
        Details on how to set up the Evaluator are in the docstring of the Evaluator class.

        Args:
            features_dict (dict): 
                a dictionary of stimulus names as keys, and corresponding voltage traces as values.
            raise\_ (bool): Whether or not to raise an error if the required voltage trace is not in `features_dict.keys()`. 
                If False, will not raise an error, and evaluate all features that can be evaluated given the provided `features_dict`. 

        Raises:
            KeyError: if the Evaluator tries to evaluate a trace with a name that is not present in `features_dict.keys()` and :paramref:`raise_` is set to ``True``.

        Returns:
            obj: Whatever the return value is of :py:attr:`Evaluator.setup.finalize_funs`. 
            Usually, this is the output of :meth:`~biophysics_fitting.hay_evaluation_default_complete_setup_python.get_Evaluator`,        
        '''
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
