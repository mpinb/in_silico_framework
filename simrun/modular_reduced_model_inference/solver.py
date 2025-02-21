"""Optimize a cost function.

This module implements solvers that can optimize a given cost function by adapting a vector of free parameters :math:`\mathbf{x}`.
The cost function is usually defined by a :py:class:`~simrun.modular_reduced_model_inference.strategy._Strategy` object.

Different solvers can be defined here, to provide different optimization schemes.
"""


from functools import partial
import scipy.optimize

class _Solver(object):
    """Solver base class
    
    Each child must implement the :py:meth:`_setup_optimizer` method.
    
    Attributes:
        name (str): name of the solver
        optimize (callable): The solver-specific optimization function.
        strategy (:py:class:`~simrun.modular_reduced_model_inference.strategy._Strategy`): 
            The strategy object. This is set during :py:meth:`setup`.
    """
    def __init__(self, name):
        """
        Args:
            name (str): name of the solver
        """
        self.name = name
        
        # set by setup
        self.strategy = None
        self.optimize = None

    def setup(self, strategy):
        """Setup the solver for a given strategy and optimizer.
        
        The strategy needs to be passed as an argument, while the optimizer is set by the :py:meth:`_setup_optimizer` method.
        
        Args:
            strategy (:py:class:`~simrun.modular_reduced_model_inference.strategy._Strategy`): The strategy object.
        """
        # set strategy
        self.strategy = strategy
        # strategy-specific setup
        self._setup_optimizer()

    def _setup_optimizer(self):
        """Set up the optimization strategy.
        
        This method is overloaded by child classes to set the optimizer.
        
        Example:
            :py:meth:`Solver_COBYLA._setup_optimizer`
        """
        pass

    def optimize_all_splits(self, client=None, workers=None):
        """Optimize the cost function for all splits of the strategy.
        
        Args:
            client (:py:class:`dask.distributed.Client`): A dask client object.
            workers (list): List of worker names. Passed to :py:meth:`dask.distributed.Client.submit`
            
        Returns:
            dict: A dictionary with the keys being the split names and the values being the optimization results.
            
        See also:
            :py:meth:`~simrun.modular_reduced_model_inference.solver._Solver.optimize_one_split`
        """
        out = {}
        for name, split in self.strategy.DataSplitEvaluation.splits.iteritems():
            x0 = self.strategy._get_x0()
            self.strategy.set_split(split['train'])
            if client:
                out[name] = client.submit(self.optimize, x0=x0, workers=workers)
            else:
                out[name] = self.optimize(x0=x0)
        self.strategy.DataSplitEvaluation.add_result(self, out)
        return out


    def optimize_one_split(self, client=None, workers=None, index=0):  #rieke
        """Optimize the cost function for a single split.
        
        Args:
            client (:py:class:`dask.distributed.Client`): A dask client object.
            workers (list): List of worker names. Passed to :py:meth:`dask.distributed.Client.submit`
            index (int): 
                Index of the split to optimize.
                Splits are saved as a dictionary in the
                :py:attr:`~simrun.modular_reduced_model_inference.strategy.DataSplitEvaluation.splits` attribute.
                The index then refers to the index of the names (i.e. keys) of the splits.
                Note that dictionaries are in general unordered, so this index is only useful to differentiate between splits,
                not to refer to a specific split or order of splits.
            
        Returns:
            dict: A dictionary with the optimization results.
        """
        out = {}
        names = sorted(self.strategy.DataSplitEvaluation.splits.keys())
        #         for name, split in self.strategy.DataSplitEvaluation.splits.iteritems():
        name = names[index]
        split = self.strategy.DataSplitEvaluation.splits[name]
        x0 = self.strategy._get_x0()
        self.strategy.set_split(split['train'])
        if client:
            out[name] = client.submit(self.optimize, x0=x0, workers=workers)
        else:
            out[name] = self.optimize(x0=x0)
        self.strategy.DataSplitEvaluation.add_result(self, out)
        return out


class Solver_COBYLA(_Solver):
    """COBYLA solver strategy for reduced models.
    
    See also:
        :py:mod:`~simrun.modular_reduced_model_inference.strategy` for available strategies and their
        respective objective functions.
    
    Attributes:
        name (str): name of the solver
        optimize (callable): 
            Optimization function: :py:meth:`scipy.optimize.minimize` with ``method='COBYLA'``.
            Optimization function need an objective function to minimize.
            These objecetive functions depend on the strategy.
    """

    def __init__(self, name):
        """
        Args:
            name (str): name of the solver
        """
        self.name = name
        
        # set by _setup
        self.strategy = None
        self.optimize = None

    def _setup_optimizer(self):
        """Set up the optimization strategy.
        """
        self.optimize = partial(
            self._optimize,
            self.strategy._objective_function,
            maxiter=5000)

    @staticmethod
    def _optimize(_objective_function, maxiter=5000, x0=None):
        """Static optimization method.
        
        This method is the core optimizer. It minimizes :paramref:`_objective_function` using
        :py:meth:`scipy.optimize.minimize` with ``method='COBYLA'``.
        
        Args:
            _objective_function (callable): 
                A strategy-specific objective function.
            
        """
        out = scipy.optimize.minimize(
            _objective_function,
            x0,
            method='COBYLA',
            options=dict(maxiter=maxiter, disp=True))
        return out
