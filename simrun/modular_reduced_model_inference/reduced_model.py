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

"""Construct reduced models and run optimization.

This module provides a top-level class to run reduced model inference.
Each reduced model contains:
- a :py:class:~`DataView` object to access data
- a :py:class:`DataSplitEvaluation` object to split data and evaluate the optimization results
- one or more :py:class:`~simrun.modular_reduced_model_inference.data_extractor.DataExtractor` objects to preprocess the data
- one or more :py:class:`~simrun.modular_reduced_model_inference.strategy._Strategy` objects to run the optimization.

The optimization run optimizes a set of free parameters :math:`\mathbf{x}` to minimize a cost function. 
Both the cost function and the free parameters are defined in the :py:class:`~simrun.modular_reduced_model_inference.strategy._Strategy` object.
"""


import numpy as np
import pandas as pd
from config.isf_logging import logger


def get_n_workers_per_ip(workers, n):
    '''Convenience method to get a certain amount of workers per machine

    Groups all workers by their IP, fetches :paramref:`n` workers per IP,
    and returns them as a list.

    Args:
        workers (List[dask.distributed.worker.Worker]):
            List or array of dask workers.
        n (int): Amount fo workers to fetch per machine.

    Returns:
        List[dask.distributed.worker.Worker]: List of :paramref:`n`*``n_machines`` workers.
    '''
    s = pd.Series(workers)
    return s.groupby(s.str.split(':').str[1]).apply(lambda x: x[:n]).tolist()


class Rm(object):
    r"""Reduced model class.
    
    This is the top-level class for running reduced model inference.
    It provides an interface to add data extractors and strategies, and to run the optimization.
    
    Attributes:
        name (str): Name of the reduced model
        db (str): Path to the database
        tmin (float): Minimum time for the simulation
        tmax (float): Maximum time for the simulation
        width (float): Width of the temporal kernel. 
            This will be used as the domain e.g. the :math:`\\tau` domain in :py:class:`~simrun.modular_reduced_model_inference.strategy.RaisedCosineBasis`
        n_trials (int): Amount of trials
        data_extractors (dict): Dictionary of :py:class:`~simrun.modular_reduced_model_inference.data_extractor._DataExtractor` objects
        strategies (dict): Dictionary of :py:class:`~simrun.modular_reduced_model_inference.strategy.Strategy` objects
        Data (:py:class:`~simrun.modular_reduced_model_inference.reduced_model.DataView`): Data view object
        DataSplitEvaluation (:py:class:`~simrun.modular_reduced_model_inference.reduced_model.DataSplitEvaluation`): Data split evaluation object
        selected_indices (list): List/nested list of integer indices for selected simulation trials
        results_remote (bool): Flag that keeps track whether results are stored locally or on a remote scheduler.
    """
    def __init__(
        self,
        name,
        db,
        tmin=None,
        tmax=None,
        width=None,
        selected_indices=None):
        """
        Args:
            name (str): Name of the reduced model
            db (str): Path to the database
            tmin (float): Minimum time for the simulation
            tmax (float): Maximum time for the simulation
            width (float): Width of the temporal kernel. This will be used as the :math:`\\tau` domain in e.g. :py:class:`~simrun.modular_reduced_model_inference.strategy.RaisedCosineBasis`
            selected_indices (list): List/nested list of integer indices for selected simulation trials
        """
        self.name = name
        self.db = db
        self.tmax = tmax
        self.tmin = tmin
        self.width = width
        self.n_trials = None
        self.data_extractors = {}
        self.strategies = {}
        self.Data = DataView()
        self.Data.setup(self)
        self.DataSplitEvaluation = DataSplitEvaluation(self)
        self.selected_indices = selected_indices  # list/nested list of integer indices for selected simulation trials
        # for remote optimization
        self.results_remote = False  # flag, false if we have all results locally

    def add_data_extractor(self, name, data_extractor, setup=True):
        """Add a data extractor to the reduced model.
        
        Data extractors are used to preprocess the data so that the strategies can use them.
        
        Args:
            name (str): Name of the data extractor
            data_extractor (:py:class:`~simrun.modular_reduced_model_inference.data_extractor._DataExtractor`): Data extractor object
            setup (bool): If True, run the setup method of the data extractor
            
        See also:
            :py:mod:`~simrun.modular_reduced_model_inference.data_extractor` for available data extractors.
        """
        self.data_extractors[name] = data_extractor
        if setup == True:
            data_extractor.setup(self)

    def add_strategy(self, strategy, setup=True, view=None):
        """Add a strategy to the reduced model.
        
        Args:
            strategy (:py:class:`~simrun.modular_reduced_model_inference.strategy.Strategy`): Strategy object
            setup (bool): If True, run the setup method of the strategy
            view (:py:class:`~simrun.modular_reduced_model_inference.reduced_model.DataView`): Data view object
            
        See also:
            :py:mod:`~simrun.modular_reduced_model_inference.strategy` for available strategies.
            :py:mod:`DataView` for the data view object.
        """
        name = strategy.name
        assert name not in self.strategies.keys()
        self.strategies[name] = strategy
        if view is None:
            view = self.Data
        if setup:
            strategy.setup(view, self.DataSplitEvaluation)

    def get_n_trials(self):
        """Get the amount of trials.
        
        If the amount of trials is not set, it is set to the length of the data.
        
        Returns:
            int: Amount of trials
        """
        if self.n_trials is None:
            self.n_trials = len(self.Data['y'])
        return self.n_trials

    def extract(self, name):
        """Extract data using the data extractor.
        
        Args:
            name (str): Name of the data extractor
            
        Returns:
            obj: Data extracted by the data extractor
            
        See also:
            :py:meth:`~simrun.modular_reduced_model_inference.data_extractor>get` for how a data extractor fetches data.
        """
        return self.data_extractors[name].get()

    def run(self, client=None, n_workers=None, strategy_selection=None):
        """Run one or more strategies on the data.
        
        A strategy is a pipeline that:
        
        1. Extracts data from the reduced model
        2. Splits the data into training and test sets
        3. Constructs a cost function to be optimized.
        4. Solves the optimization problem using a :py:class:`~simrun.modular_reduced_model_inference.solver._Solver`
        
        Each strategy implements different cost functions, depending on what to optimize for.
        However, they all implement a :py:meth:`get_score` method to evaluate the performance of the optimization.
        
        Args:
            client (:py:class:`~dask.distributed.Client`): Dask client for remote optimization
            n_workers (int): Amount of workers to use for remote optimization
            strategy_selection (list): List of strategy names to run. If None, run all strategies.
            
        See also:
            :py:mod:`simrun.modular_reduced_model_inference.strategy` for available strategies.
        
        """
        for strategy_name in sorted(self.strategies.keys()):

            # 1. Extract the strategy to apply
            if strategy_selection is not None:
                if not strategy_name in strategy_selection:
                    continue
            strategy = self.strategies[strategy_name]

            # 2. Solve for this strategy
            for solver_name in sorted(strategy.solvers.keys()):
                solver = strategy.solvers[solver_name]
                if client is not None:
                    logger.info(
                        'Starting remote optimization: strategy {} with solver {}'.format(strategy_name, solver_name))
                    workers = client.scheduler_info()['workers'].keys()
                    workers = get_n_workers_per_ip(workers, n_workers)
                    solver.optimize_all_splits(client, workers=workers)
                    self.results_remote = True
                else:
                    logger.info(
                        'Starting local optimization: strategy {} with solver {}'.format(strategy_name, solver_name))
                    solver.optimize_all_splits()

    def _gather_results(self, client):
        """Fetch the solver results from the dask scheduler.
        
        Args:
            client (:py:class:`~dask.distributed.Client`): Dask client.
        """
        assert client is not None
        self.DataSplitEvaluation.optimizer_results = \
            client.gather(self.DataSplitEvaluation.optimizer_results)
        self.results_remote = False

    def get_results(self, client=None):
        """Get the results of the optimization.
        
        Args:
            client (:py:class:`~dask.distributed.Client`): Dask client.
            
        Returns:
            pd.DataFrame: DataFrame with the optimization results.
            
        See also:
            :py:meth:`~simrun.modular_reduced_model_inference.reduced_model.DataSplitEvaluation.compute_scores` for how the scores are computed and their output format.
        """
        if self.results_remote:
            self._gather_results(client)
        return self.DataSplitEvaluation.compute_scores()


class DataView(object):
    """Convenience wrapper class to access data.

    This wrapper class redirects data extractors based on a key mapping.
    This API is used by default in :py:class:`~simrun.modular_reduced_model_inference.Rm`
    If no mapping is provided, or a requested key does not exist in the mapping, the original key is used instead.

    Example:

        >>> data = {'a': 1, 'b': 2}
        >>> dv = DataView()
        >>> dv.setup(Rm)
        >>> dv['a']
        1
        >>> dv.mapping_dict = {'a': 'b'}
        >>> dv['a']
        2
    
    Attributes:
        mapping_dict (dict):
            Mapping between requested keys and target keys.
            Used to redirect data fetching.
        Rm (:py:class:`Rm`):
            Reduced model. Set after running :py:meth:`setup`
    """

    def __init__(self, mapping_dict = None):
        """
        Args:
            mapping_dict (dict): 
                Mapping between requested keys and target keys.
                Used to redirect data fetching.
        """
        mapping_dict = mapping_dict or {}
        self.mapping_dict = mapping_dict

    def setup(self, Rm):
        """Initialize from a reduced model.

        Allow access to parent :py:class:`Rm` attributes.

        Args:
            Rm (:py:class:`Rm`): The reduced model to initialize from.
        """
        self.Rm = Rm

    def __getitem__(self, key):
        """Fetch data from key.

        If the key exists in :paramref:`mapping_dict`, return the data
        associated to the key redirect instead.

        Args:
            key (str): The key to fetch.
        """
        if not key in self.mapping_dict:
            return self.Rm.extract(key)
        else:
            return self.Rm.extract(self.mapping_dict[key])


class DataSplitEvaluation(object):
    '''Split data in training-test sets.
    
    This class provides an interface to split input data in separate train-test sets,
    and to evaluate the reduced model performance scores corresponding to the splits.
    
    Attributes:
        Rm (:py:class:`Rm`): Reduced model. Set after running :py:meth:`setup`
        splits (dict): Dictionary of splits
        solvers (list): List of solvers
        optimizer_results (list): List of optimization results
        optimizer_results_keys (list): List of optimization results keys
        scores (list): List of scores
        scores_keys (list): List of scores
    '''

    def __init__(self, Rm):
        """
        Args:
            Rm (:py:class:`Rm`): Reduced model. Set after running :py:meth:`setup`
        """
        self.Rm = Rm
        self.splits = {}
        self.solvers = []
        self.optimizer_results = []
        self.optimizer_results_keys = []
        self.scores = []
        self.scores_keys = []

    def add_random_split(self, name, percentage_train=.7, l=None):
        """Set the train-test split randomly.
        
        Args:
            name (str): Name of the split
            percentage_train (float): Percentage of trials to use for training
            l (list): List of indices to use for the split. If None, use all trials.
            
        Raises:
            AssertionError: If the split name already exists.
        """
        assert name not in self.splits.keys()
        if l is None:
            n = self.Rm.get_n_trials()
            l = range(n)
        else:
            n = len(l)
        np.random.shuffle(np.array(l))
        train = l[:int(n * percentage_train)]
        test = l[int(n * percentage_train):]
        subtest1 = test[:int(len(test) / 2)]
        subtest2 = test[int(len(test) / 2):]
        self.splits[name] = {
            'train': train,
            'test': test,
            'subtest1': subtest1,
            'subtest2': subtest2
        }

    def add_isi_dependent_random_split(
        self,
        name,
        min_isi=10,
        percentage_train=.7):
        """Split data based on the inter-spike interval.
        
        This method filters out trials with an inter-spike interval below a certain threshold.
        Only then the data is split into a train-test split.
        
        Args:
            name (str): Name of the split
            min_isi (float): Minimum inter-spike interval
            percentage_train (float): Percentage of trials to use for training
        
        Raises:
            AssertionError: If the split name already exists.
        """
        assert name not in self.splits.keys()
        ISI = self.Rm.extract('ISI') * -1
        ISI = ISI.fillna(min_isi + 1)
        ISI = ISI.reset_index(drop=True)
        l = list(ISI[ISI >= min_isi].index)
        self.add_random_split(name, percentage_train=percentage_train, l=l)

    def get_splits(self):
        """Get the train-test splits.
        
        Returns:
            dict: Dictionary of train-test splits, where the keys are the split names.
                Each split is a dictionary with keys ``'train'``, ``'test'``, ``'subtest1'``, ``'subtest2'``.
        """
        return self.splits

    def add_result(self, solver, x):
        """Save the optimization result.
        
        All relevant info on which solver and strategy was used is then available under the attributes:
        ``strategy``, ``solver``, and ``run``.
        
        Args:
            solver (:py:class:`~simrun.modular_reduced_model_inference.solver._Solver`): Solver object
            x (dict): Optimization result        
        """
        #         assert len(self.splits) == len(x) #rieke - want to run individual splits sometimes
        # assert solver.strategy.Rm is self.Rm
        solver_name = solver.name
        strategy_name = solver.strategy.name
        run_number = len([
            k for k in self.optimizer_results_keys
            if k[0] == strategy_name and k[1] == solver_name
        ])
        self.optimizer_results_keys.append((strategy_name, solver_name, run_number))
        self.optimizer_results.append(x)
        self.solvers.append(solver)

    def compute_scores(self):
        """Compute the score of the optimization.
        
        This method extracts the optimization results and computes the resulting score of the cost function.
        
        See also:
            :py:meth:`~simrun.modular_reduced_model_inference.strategy.Strategy._objective_function` for the cost function.
        
        Returns:
            pd.DataFrame: DataFrame with the optimization results.
        """
        strategy_index = []
        solver_index = []
        split_index = []
        subsplit_index = []
        success_index = []
        score_index = []
        x_index = []
        runs_index = []
        
        for k, solver, x in zip(self.optimizer_results_keys, self.solvers, self.optimizer_results):
            for split_name, xx in x.iteritems():
                split = self.splits[split_name]
                for subsplit_name, subsplit in split.iteritems():
                    runs_index.append(k[2])
                    x_index.append(xx.x)
                    success_index.append(xx.success)
                    solver_index.append(solver.name)
                    strategy = solver.strategy
                    strategy_index.append(strategy.name)
                    split_index.append(split_name)
                    subsplit_index.append(subsplit_name)
                    # calculate score
                    score = strategy.set_split(subsplit)._objective_function(xx.x)
                    score_index.append(score)
        out = {
            'strategy': strategy_index,
            'solver': solver_index,
            'split': split_index,
            'subsplit': subsplit_index,
            'run': runs_index,
            'score': score_index,
            'x': x_index,
            'success': success_index
        }
        out = pd.DataFrame(out)
        out = out.set_index(
            ['strategy', 'solver', 'split', 'subsplit','run']
            ).sort_index()
        return out
