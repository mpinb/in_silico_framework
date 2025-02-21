"""Multi-objective optimization algorithm.

This code has been adapted from [BluePyOpt](https://github.com/BlueBrain/BluePyOpt) :cite:`Van_Geit_Gevaert_Chindemi_Roessert_Courcol_Muller_Schuermann_Segev_Markram_2016`
such that:

- a start population can be defined.
- such that the optimizations can be organized in a data base.
- to be executed on a distributed system using dask.
- to return all objectives, not only the combined ones.

The main interface is the function :py:meth:`start_run`.

Note: 
    Part of this module is licensed under the GNU Lesser General Public License version 3.0 as published by the Free Software Foundation:
    
    Copyright (c) 2016, EPFL/Blue Brain Project. 
    Part of this file is part of BluePyOpt <https://github.com/BlueBrain/BluePyOpt>. 
    This library is free software; you can redistribute it and/or modify it under
    the terms of the GNU Lesser General Public License version 3.0 as published
    by the Free Software Foundation. 
    This library is distributed in the hope that it will be useful, but WITHOUT 
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
    FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more 
    details. 
    You should have received a copy of the GNU Lesser General Public License
    along with this library; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""
import time

import bluepyopt as bpop
import deap
import distributed
import numpy
import pandas as pd
import six
from bluepyopt.deapext import algorithms
from bluepyopt.deapext.optimisations import WSListIndividual
from distributed.client import CancelledError
from distributed.scheduler import KilledWorker

from data_base.IO.LoaderDumper import \
    pandas_to_msgpack as dumper_pandas_to_msgpack
from data_base.IO.LoaderDumper import \
    pandas_to_parquet as dumper_pandas_to_parquet
from data_base.IO.LoaderDumper import to_pickle as dumper_to_pickle
from data_base.utils import wait_until_key_removed


def robust_int(x):
    """Robustly convert something to an integer.
    
    Returns None if the conversion is not possible.
    
    Args:
        x: The object to be converted.
        
    Returns:
        int | None: The converted object."""
    try:
        return int(x)
    except:
        return None


def get_max_generation(db_run):
    '''Returns the index of the next iteration in a database. 
    If the database is empty, it returns -1.
    
    Args:
        db_run (data_base.DataBase): The database.
        
    Returns:
        int: The index of the next iteration. If the database is empty, it returns -1.'''
    keys = [
        robust_int(x) for x in list(db_run.keys()) if robust_int(x) is not None
    ]
    if not keys:
        current_key = -1
    else:
        current_key = max(keys)
    return current_key


def save_result(db_run, features, objectives):
    """Save the results of an optimization iteration in a database.
    
    Args:
        db_run (data_base.DataBase): The database.
        features (pd.DataFrame): The features of the optimization iteration.
        objectives (pd.DataFrame): The objectives of the optimization iteration.
    
    Returns:
        None. The results are saved in the database."""
    current_key = get_max_generation(db_run) + 1
    if six.PY2:
        dumper = dumper_pandas_to_msgpack
    elif six.PY3:
        dumper = dumper_pandas_to_parquet
    else:
        raise RuntimeError()
    db_run.set(
        str(current_key),
        pd.concat([objectives, features], axis=1),
        dumper=dumper)


def setup_db_run(db_setup, run):
    '''Create a sub-database for each run of the optimization algorithm.
    db_setup contains a sub db for each run of the full optimization. This sub db is created here.
    
    Args:
        db_setup (data_base.DataBase): The database containing the setup of the optimization.
        run (int): The index of the optimization run.
        
    Returns:
        data_base.DataBase: The database for the optimization run containing sub-databases..'''
    if not str(run) in list(db_setup.keys()):
        db_setup.create_sub_db(str(run))
    db_run = db_setup[str(run)]
    db_run['0'] = ''
    if not 'checkpoint' in list(db_run.keys()):
        db_run.create_managed_folder('checkpoint')
    return db_run


def get_objective_function(db_setup):
    """Get the objective function for the optimization.
    
    This objective function takes parameters values, runs a simulation, and evaluates the simulation.
    
    Args:
        db_setup (data_base.DataBase): The database containing the setup of the optimization.
        
    Returns:
        function: The objective function for the optimization."""
    parameter_df = db_setup['params']
    Simulator = db_setup['get_Simulator'](db_setup)
    Evaluator = db_setup['get_Evaluator'](db_setup)

    def objective_function(param_values):
        p = pd.Series(param_values, index=parameter_df.index)
        s = Simulator.run(p)
        e = Evaluator.evaluate(s)
        # ret is not a list but a dict!
        # however, bluepyopt expects a list. The conversion is performed in a custom mymap function
        # in the mymap function, the result is also stored
        return e

    return objective_function


def get_mymap(db_setup, db_run, c, satisfactory_boundary_dict=None, n_reschedule_on_runtime_error = 3):
    """Get a map function for evaluating the parameters.
    
    This function is a hook into bluePyOpt's optimization.
    It is used as a mapping function in :py:class:`bluepyopt.optimisations.DEAPOptimisation` during :py:meth:`start_run`.
    Rather than just returning the combined objectives, it also saves the features and the objectives in the database.
    This is useful for debugging and for analyzing the optimization results.
    
    Args:
        db_setup (:py:class:`~data_base.data_base.DataBase`): The database containing the setup of the optimization.
        db_run (:py:class:`~data_base.data_base.DataBase`): The database for the optimization run containing sub-databases.
        c (:py:class:`~dask.distributed.Client`): The distributed client.
        satisfactory_boundary_dict (dict | None): A dictionary with the boundaries for the objectives. If a model is found, that has all objectives below the boundary, the optimization is stopped.
        n_reschedule_on_runtime_error (int): The number of times the optimization is rescheduled if a runtime error occurs.
        
    Returns:
        Callable: The map function for evaluating the parameters. this function is passed to the :py:class:`bluepyopt.optimisations.DEAPOptimisation` object.    
    """
    # CAVE! get_mymap is doing more than just returning a map function.
    # - the map function ignores the first argument.
    #   The first argument (i.e. the function to be mapped on the iterable) is ignored.
    #   Instead, that function is hardcoded. It is defined in db_setup['get_Evaluator']
    #   This was neccessary, as my_ibea_evaluator and the deap individuals were causing pickle errors
    # - mymap also saves the features. As the bluepyopt optimizer only sees the summarized
    #   features (maximum of several individual features, see Hay et. al.), mymap is the ideal
    #   place to insert a routine that saves all features before they get sumarized.
    # - mymap also creates a sub db in db_setup. The name of the sub_db is specified by n: It is str(n)
    #   db_setup[str(n)] then contains all the saved results    objective_fun = get_objective_function(db_setup)
    combiner = db_setup['get_Combiner'](db_setup)
    params = db_setup['params'].index
    objective_fun = get_objective_function(db_setup)

    def mymap(func, iterable):
        params_list = list(map(list, iterable))
        params_pd = pd.DataFrame(params_list, columns=params)
        futures = c.map(objective_fun, params_list, pure=False)
        try:
            features_dicts = c.gather(futures)
        except (distributed.client.CancelledError, distributed.scheduler.KilledWorker):
            print('Futures have been canceled. Waiting for 3 Minutes, then reschedule.')
            del futures
            time.sleep(3 * 60)
            print('Rescheduling ...')
            return mymap(func, iterable)
        except RuntimeError:
            if reschedule_on_runtime_error >= 0:
                print(
                    'Got a RuntimeError while gathering futures. This may be dask related, or it may be a RuntimeError raised by the' + 
                    'Evaluator. Remaining attempts: {}. Waiting for 3 Minutes, then reschedule.'.format(reschedule_on_runtime_error)
                )
                return mymap(func, iterable, n_reschedule_on_runtime_error = n_reschedule_on_runtime_error - 1)
            else:
                raise 
        except:
            distributed.wait(futures)
            for lv, f in enumerate(futures):
                if not f.status == 'finished':
                    errstr = 'Problem with future number {}\n'.format(lv)
                    errstr += 'Exception: {}:{}\n'.format(
                        type(f.exception()), f.exception())
                    errstr += 'Parameters are: {}\n'.format(
                        dict(params_pd.iloc[lv]))
                    raise ValueError(errstr)
        
        # features_dicts = map(objective_fun, params_list) # temp rieke
        features_dicts = c.gather(futures)  #temp rieke
        features_pd = pd.DataFrame(features_dicts)
        
        # save the parameters and the features in the database
        save_result(db_run, params_pd, features_pd)
        
        # combine the objectives
        combined_objectives_dict = list(map(combiner.combine, features_dicts))
        combined_objectives_lists = [
            [d[n]
            for n in combiner.setup.names]
            for d in combined_objectives_dict
            ]

        # label a "good" model if dict with boundaries for different objectives is given
        if satisfactory_boundary_dict:
            assert satisfactory_boundary_dict.keys() == combined_objectives_dict[0].keys()
            all_err_below_boundary = [
                all(dict_[key] <= satisfactory_boundary_dict[key]
                for key in dict_.keys())
                for dict_ in combined_objectives_dict
                ]
            if any(all_err_below_boundary):
                db_setup['satisfactory'] = [
                    i for (i, x) in enumerate(all_err_below_boundary) if x
                    ]


         # all_err_below_3 = [all(x<3 for x in list(dict_.values())) for dict_ in combined_objectives_dict]
         # if any(all_err_below_3):
         #     db_setup['satisfactory'] = [i for (i,x) in enumerate(all_err_below_3) if x]

        return numpy.array(combined_objectives_lists)

    return mymap


class my_ibea_evaluator(bpop.evaluators.Evaluator):
    """
    Graupner-Brunel Evaluator
    
    .. deprecated:: 0.4.0
        Evaluation is done with :py:meth:`mymap`.
    
    :skip-doc:
    """

    def __init__(self, parameter_df, n_objectives):
        """Constructor"""
        super(my_ibea_evaluator, self).__init__()
        assert isinstance(
            parameter_df, pd.DataFrame
        )  # we rely on the fact that the dataframe has an order
        self.parameter_df = parameter_df
        self.params = [
            bpop.parameters.Parameter(index, bounds=(x['min'], x['max']))
            for index, x in parameter_df.iterrows()
        ]

        self.param_names = list(parameter_df.index)
        self.objectives = [1] * n_objectives

    def evaluate_with_lists(self, param_values):
        return None  # because of serialization issues, evaluate with lists is unused.
        # Instead, the mymap function defines which function is used to evaluate the parameters!!!


############################################################
# the following is taken from bluepyopt.deapext.algorithms.py
# it is changed such that the checkpoint only saves the population, but not the history
# and hall of fame, as this can be easily reconstructed from the data saved by
# mymap
############################################################
"""Optimisation class"""
"""
Copyright (c) 2016, EPFL/Blue Brain Project
 This file is part of BluePyOpt <https://github.com/BlueBrain/BluePyOpt>
 This library is free software; you can redistribute it and/or modify it under
 the terms of the GNU Lesser General Public License version 3.0 as published
 by the Free Software Foundation.
 This library is distributed in the hope that it will be useful, but WITHOUT
 ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
 details.
 You should have received a copy of the GNU Lesser General Public License
 along with this library; if not, write to the Free Software Foundation, Inc.,
 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

# pylint: disable=R0914, R0912

import logging
import pickle
import random

import deap.algorithms
import deap.tools

logger = logging.getLogger('__main__')


def _evaluate_invalid_fitness(toolbox, population):
    '''Evaluate the individuals with an invalid fitness
    Returns the count of individuals with invalid fitness
    '''
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    return len(invalid_ind)


def _update_history_and_hof(halloffame, history, population):
    '''Update the hall of fame with the generated individuals
    Note: History and Hall-of-Fame behave like dictionaries
    '''
    if halloffame is not None:
        halloffame.update(population)

    history.update(population)


def _record_stats(stats, logbook, gen, population, invalid_count):
    '''Update the statistics with the new population'''
    record = stats.compile(population) if stats is not None else {}
    logbook.record(gen=gen, nevals=invalid_count, **record)


def _get_offspring(parents, toolbox, cxpb, mutpb):
    '''return the offsprint, use toolbox.variate if possible'''
    if hasattr(toolbox, 'variate'):
        return toolbox.variate(parents, toolbox, cxpb, mutpb)
    return deap.algorithms.varAnd(parents, toolbox, cxpb, mutpb)


def eaAlphaMuPlusLambdaCheckpoint(
        population,
        toolbox,
        mu,
        cxpb,
        mutpb,
        ngen,
        stats=None,
        halloffame=None,
        cp_frequency=1,
        db_run=None,
        continue_cp=False,
        db=None):
    r"""This is the :math:`(~\alpha,\mu~,~\lambda)` evolutionary algorithm
    
    Args:
        population (list): list of deap Individuals
        toolbox(deap Toolbox)
        mu (int): Total parent population size of EA
        cxpb (float): Crossover probability
        mutpb (float): Mutation probability
        ngen (int): Total number of generation to run
        stats (deap.tools.Statistics): generation of statistics
        halloffame (deap.tools.HallOfFame): hall of fame
        cp_frequency (int): generations between checkpoints
        cp_filename (DataBase or None): db_run, where the checkpoint is stored in [generation]_checkpoint. Was: path to checkpoint filename
        continue_cp (bool): whether to continue
    """
    # --- added by arco
    if db_run is not None:
        assert db_run.__class__.__name__ in ("ModelDataBase", "ISFDataBase")  # db_run
    assert halloffame is None
    # --- end added by arco

    if continue_cp:
        # A file name has been given, then load the data from the file
        key = '{}_checkpoint'.format(get_max_generation(db_run))
        cp = db_run[key]  #pickle.load(open(cp_filename, "r"))
        population = cp["population"]
        parents = cp["parents"]
        start_gen = cp["generation"]
        halloffame = cp["halloffame"]
        logbook = cp["logbook"]
        history = cp["history"]
        random.setstate(cp["rndstate"])
        print('continuing optimization from generation {}'.format(start_gen))
    else:
        # Start a new evolution
        start_gen = 1
        parents = population[:]

        ## commented out by arco ... as we record every evaluation, we do not need the bluepyopt history as it slows down the iteration
        #logbook = deap.tools.Logbook()
        #logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])
        #history = deap.tools.History()
        ## end commented out by arco

        # TODO this first loop should be not be repeated !
        invalid_count = _evaluate_invalid_fitness(toolbox, population)
        ## commented out by arco ... as we record every evaluation, we do not need the bluepyopt history as it slows down the iteration
        #_update_history_and_hof(halloffame, history, population)
        #_record_stats(stats, logbook, start_gen, population, invalid_count)
        ## end commented out by arco

    # Begin the generational process
    for gen in range(start_gen + 1, ngen + 1):

        if db is not None:
            wait_until_key_removed(db, 'pause')

        offspring = _get_offspring(parents, toolbox, cxpb, mutpb)

        population = parents + offspring

        invalid_count = _evaluate_invalid_fitness(toolbox, offspring)
        ## commented out by arco
        #_update_history_and_hof(halloffame, history, population)
        #_record_stats(stats, logbook, gen, population, invalid_count)
        ## end commented out by arco

        # Select the next generation parents
        parents = toolbox.select(population, mu)

        ## commented out by arco
        #logger.info(logbook.stream)
        ## end commented out by arco

        if (db_run and cp_frequency and gen % cp_frequency == 0):
            cp = dict(
                population=population,
                generation=gen,
                parents=parents,
                halloffame=None,  #halloffame, // arco
                history=None,  # history, // arco
                logbook=None,  # logbook, // arco
                rndstate=random.getstate())
            # save checkpoint in db
            db_run.set('{}_checkpoint'.format(gen),
                            cp,
                            dumper=dumper_to_pickle)
            #pickle.dump(cp, open(cp_filename, "wb"))
            #logger.debug('Wrote checkpoint to %s', cp_filename)

        if 'satisfactory' in db.keys(
        ) and gen > 1:  #gen>1 to make sure a checkpoint is created
            break

    return population  #, logbook, history


####################################################
# end taken from bluepyopt
#####################################################


def run(
        self,
        max_ngen=10,
        offspring_size=None,
        continue_cp=False,
        cp_filename=None,
        cp_frequency=1,
        pop=None,
        db=None
        ):
    """
    This method is a class method of the BluePyOpt optimisations.DEAPOptimisation class.
    It is extended here such that a start population can be defined.
    Running actual optimization is done with the :meth:`~biophysics_fitting.optimizer.start_run`, which further extends this method.
    
    Note: 
        the population needs to be in a special format. Use methods in biophysics_fitting.population 
        to create a population.
    """
    # Allow run function to override offspring_size
    # TODO probably in the future this should not be an object field anymore
    # keeping for backward compatibility
    if offspring_size is None:
        offspring_size = self.offspring_size

    # Generate the population objec
    if pop is None:
        pop = self.toolbox.population(n=offspring_size)
    else:
        print("initialized with population of size {:s}".format(len(pop)))
        assert continue_cp == False

    ## commented out by arco
    #stats = deap.tools.Statistics(key=lambda ind: ind.fitness.sum)
    #import numpy
    #stats.register("avg", numpy.mean)
    #stats.register("std", numpy.std)
    #stats.register("min", numpy.min)
    #stats.register("max", numpy.max)
    ## end commented out by arco

    pop = eaAlphaMuPlusLambdaCheckpoint(
        pop,
        self.toolbox,
        offspring_size,
        self.cxpb,
        self.mutpb,
        max_ngen,
        stats=None,  # arco
        halloffame=None,  # self.hof,
        cp_frequency=cp_frequency,
        continue_cp=continue_cp,
        cp_filename=cp_filename,
        db=db)

    return pop


def get_population_with_different_n_objectives(old_pop, n_objectives):
    '''Adapt the number of objectives of individuals
    
    Args:
        old_pop: list of deap.Individuals
        n_objectives (int): number of objectives
        
    Returns:
        list of deap.Individuals: population with adapted number of objectives'''
    pop = []
    for p in old_pop:
        ind = WSListIndividual(p, obj_size=n_objectives)
        pop.append(ind)
    return pop


def start_run(
        db_setup,
        n,
        pop=None,
        client=None,
        continue_cp=False,
        offspring_size=1000,
        eta=10,
        mutpb=0.3,
        cxpb=0.7,
        max_ngen=600,
        satisfactory_boundary_dict=None
        ):
    '''
    Start an optimization run as specified in db_setup.

    Args:
        db_setup (data_base.DataBase): a DataBase containing the setup of the optimization. It must include:
        
            - params ... this is a pandas.DataFrame with the parameternames as index and the columns min_ and max_
            - get_Simulator ... function, that returns a biophysics_fitting.simulator.Simulator object
            - get_Evaluator ... function, that returns a biophysics_fitting.evaluator.Evaluator object.
            - get_Combiner ... function, that returns a biophysics_fitting.combiner.Combiner object
                
            get_Simulator, get_Evaluator, get_Combiner accept the db_setup data_base as argument. 
            This allows, that e.g. the Simular can depend on the data_base. Therefore it is e.g. possible, 
            that the path to the morphology is not saved as absolute path. Instead, fixed parameters can be
            updated accordingly.
            
        n (int): a seedpoint for the optimization randomization.
        pop (list of deap.Individuals | None): The previous population if the optimization is continued. None if a new optimization is started.
        client (distributed.Client | None): A distributed client. If None, the optimization is run on the local machine.
        continue_cp (bool): If True, the optimization is continued. If False, a new optimization is started.
        offspring_size (int): The number of individuals in the offspring.
        eta (int): The number of parents selected for each offspring.
        mutpb (float): The mutation probability.
        cxpb (float): The crossover probability.
        max_ngen (int): The maximum number of generations.
        satisfactory_boundary_dict (dict | None): A dictionary with the boundaries for the objectives. If a model is found, that has all objectives below the boundary, the optimization is stopped.
    
        
    For an exemplary setup of a Simulator, Evaluator and Combiner object, see 
    biophysics_fitting.hay_complete_default_setup.
    
    For on examplary setup of a complete optimization project see 
    getting_started/tutorials/1. neuron models/1.3 Generation.ipynb
    
    You can also have a look at the test case in tests.test_biophysics_fitting.optimizer_test.py
    '''
    # CAVE! get_mymap is doing more, than just to return a map function.
    # - the map function ignores the first argument.
    #   The first argument (i.e. the function to be mapped on the iterable) is ignored.
    #   Instead, that function is hardcoded. It is defined in db_setup['get_Evaluator']
    #   This was neccessary, as my_ibea_evaluator and the deap individuals were causing pickle errors
    # - mymap also saves the features. As the bluepyopt optimizer only sees the sumarized
    #   features (maximum of several individual features, see Hay et. al.), mymap is the ideal
    #   place to insert a routine that saves all features before they get sumarized.
    # - mymap also creates a sub db in db_setup. The name of the sub_db is specified by n: It is str(n)
    #   db_setup[str(n)] then contains all the saved results

    db_run = setup_db_run(db_setup, n)
    mymap = get_mymap(
        db_setup,
        n,
        client,
        satisfactory_boundary_dict=satisfactory_boundary_dict)
    len_objectives = len(db_setup['get_Combiner'](db_setup).setup.names)
    parameter_df = db_setup['params']
    evaluator_fun = db_setup['get_Evaluator'](db_setup)
    evaluator = my_ibea_evaluator(parameter_df, len_objectives)
    opt = bpop.optimisations.DEAPOptimisation(
        evaluator,
        offspring_size=offspring_size,
        eta=eta,
        mutpb=mutpb,
        cxpb=cxpb,
        map_function=get_mymap(
            db_setup,
            db_run,
            client,
            satisfactory_boundary_dict=satisfactory_boundary_dict),
        seed=n)

    if continue_cp == True:
        # if we want to continue a preexisting optimization, no population may be provided
        # also check, whether the optimization really exists
        assert pop is None
        if not str(n) in list(db_setup.keys()):
            raise ValueError(
                'run {} is not in db_setup. Nothing to continue'.format(n))
    if continue_cp == False:
        # if we want to start a new optimization, ckeck that there is not an old optimizatation
        # that would be overwritten.
        if get_max_generation(db_run) > 0:
            raise ValueError(
                'for n = {}, an optimization is already in db_setup. Either choose continue_cp=True or delete the optimization.'
                .format(n))
        if pop is not None:
            # if population is provided, make sure it fits the number of objectives of the current optimization
            print((
                "recreating provided population with a number of objectives of {}"
                .format(len_objectives)))
            pop = get_population_with_different_n_objectives(
                pop, len_objectives)
        else:
            # else generate a new population
            pop = opt.toolbox.population(n=offspring_size)

    print((
        'starting multi objective optimization with {} objectives and {} parameters'
        .format(len_objectives, len(parameter_df))))

    pop = eaAlphaMuPlusLambdaCheckpoint(
        pop,
        opt.toolbox,
        offspring_size,
        opt.cxpb,
        opt.mutpb,
        max_ngen,
        stats=None,  # arco
        halloffame=None,  # self.hof,
        cp_frequency=1,
        continue_cp=continue_cp,
        db_run=db_run,
        db=db_setup)

    return pop

    pop = run(opt,
              max_ngen=max_ngen,
              cp_filename=db_run,
              continue_cp=continue_cp,
              pop=pop,
              db=db_setup)
    return pop
