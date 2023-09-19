"""Partly copy pasted from the BluePyOpt package, however extended, such that a start population can be defined.
Also extended, such that the optimizations can be organized in a model data base.
Also extended to be executed on a distributed system using dask.
Also extended to return all objectives, not only the combined ones.
Note: the population needs to be in a special format. Use methods in biophysics_fitting.population 
to create a population.

The main interface is the function start_run."""
import time
import bluepyopt as bpop
import numpy
import deap
from bluepyopt.deapext import algorithms
from bluepyopt.deapext.optimisations import WSListIndividual
import Interface as I
import six

def robust_int(x):
    try: 
        return int(x)
    except:
        return None

def get_max_generation(mdb_run):
    '''returns the index of the next iteration'''
    keys = [robust_int(x) for x in list(mdb_run.keys()) if robust_int(x) is not None]
    if not keys:
        current_key = -1
    else:
        current_key = max(keys)
    return current_key

def save_result(mdb_run, features, objectives):
    current_key = get_max_generation(mdb_run) + 1
    if six.PY2:
        dumper = I.dumper_pandas_to_msgpack
    elif six.PY3:
        dumper = I.dumper_pandas_to_parquet
    else:
        raise RuntimeError()
    mdb_run.setitem(str(current_key),
                    I.pd.concat([objectives, features], axis = 1),
                     dumper = dumper)


def setup_mdb_run(mdb_setup, run):
    '''mdb_setup contains a sub mdb for each run of the full optimization. This sub mdb is created here'''
    if not str(run) in list(mdb_setup.keys()):
        mdb_setup.create_sub_mdb(str(run))
    mdb_run = mdb_setup[str(run)]
    mdb_run['0'] = ''
    if not 'checkpoint' in list(mdb_run.keys()):
        mdb_run.create_managed_folder('checkpoint')  
    return mdb_run
         
def get_objective_function(mdb_setup):
    parameter_df = mdb_setup['params']
    Simulator = mdb_setup['get_Simulator'](mdb_setup)
    Evaluator = mdb_setup['get_Evaluator'](mdb_setup)
    def objective_function(param_values):
        p = I.pd.Series(param_values, index = parameter_df.index)
        s = Simulator.run(p)
        e = Evaluator.evaluate(s) 
        # ret is not a list but a dict!
        # however, bluepyopt expects a list. The conversion is performed in a custom mymap function
        # in the mymap function, the result is also stored
        return e
    return objective_function
    
def get_mymap(mdb_setup, mdb_run, c, satisfactory_boundary_dict = None):
    # CAVE! get_mymap is doing more, than just to return a map function.
    # - the map function ignores the first argument. 
    #   The first argument (i.e. the function to be mapped on the iterable) is ignored.
    #   Instead, that function is hardcoded. It is defined in mdb_setup['get_Evaluator']
    #   This was neccessary, as my_ibea_evaluator and the deap individuals were causing pickle errors
    # - mymap also saves the features. As the bluepyopt optimizer only sees the sumarized 
    #   features (maximum of several individual features, see Hay et. al.), mymap is the ideal 
    #   place to insert a routine that saves all features before they get sumarized.
    # - mymap also creates a sub mdb in mdb_setup. The name of the sub_mdb is specified by n: It is str(n)
    #   mdb_setup[str(n)] then contains all the saved results    objective_fun = get_objective_function(mdb_setup)
    combiner = mdb_setup['get_Combiner'](mdb_setup)
    params = mdb_setup['params'].index
    objective_fun = get_objective_function(mdb_setup)
    def mymap(func, iterable):
        params_list = list(map(list, iterable))
        params_pd = I.pd.DataFrame(params_list, columns = params)
        futures = c.map(objective_fun, params_list, pure = False)
        try:
                features_dicts = c.gather(futures)
        except (I.distributed.client.CancelledError, I.distributed.scheduler.KilledWorker):
            print('Futures have been canceled. Waiting for 3 Minutes, then reschedule.')
            del futures
            time.sleep(3*60)
            print('Rescheduling ...')
            return mymap(func, iterable)
        except:
            I.distributed.wait(futures)
            for lv, f in enumerate(futures):
                if not f.status == 'finished':
                    errstr = 'Problem with future number {}\n'.format(lv)
                    errstr += 'Exception: {}:{}\n'.format(type(f.exception()), f.exception())
                    errstr += 'Parameters are: {}\n'.format(dict(params_pd.iloc[lv]))
                    raise ValueError(errstr)
##        features_dicts = map(objective_fun, params_list) # temp rieke
        features_dicts = c.gather(futures) #temp rieke
        features_pd = I.pd.DataFrame(features_dicts)
        save_result(mdb_run, params_pd, features_pd)
        combined_objectives_dict = list(map(combiner.combine, features_dicts))
        combined_objectives_lists = [[d[n] for n in combiner.setup.names] 
                                     for d in combined_objectives_dict]

        # to label a "good" model if dict with boundaries for different objectives is given
        if satisfactory_boundary_dict:
            assert satisfactory_boundary_dict.keys() == combined_objectives_dict[0].keys()
            all_err_below_boundary = [all(dict_[key]<=satisfactory_boundary_dict[key] for key in dict_.keys()) for dict_ in combined_objectives_dict]
            if any(all_err_below_boundary):
                mdb_setup['satisfactory'] = [i for (i,x) in enumerate(all_err_below_boundary) if x]
            
#         all_err_below_3 = [all(x<3 for x in list(dict_.values())) for dict_ in combined_objectives_dict]
#         if any(all_err_below_3):
#             mdb_setup['satisfactory'] = [i for (i,x) in enumerate(all_err_below_3) if x]

        return numpy.array(combined_objectives_lists)
    return mymap

class my_ibea_evaluator(bpop.evaluators.Evaluator):

    """Graupner-Brunel Evaluator"""

    def __init__(self, parameter_df, n_objectives):
        """Constructor"""
        super(my_ibea_evaluator, self).__init__()
        assert(isinstance(parameter_df, I.pd.DataFrame)) # we rely on the fact that the dataframe has an order
        self.parameter_df = parameter_df
        self.params = [bpop.parameters.Parameter
                       (index, bounds=(x['min'], x['max']))
                       for index, x in parameter_df.iterrows()]

        self.param_names = list(parameter_df.index)
        self.objectives = [1]*n_objectives 

    def evaluate_with_lists(self, param_values):
        return None # because of serialization issues, evaluate with lists is unused. 
        # Instead, the mymap function defines, which function is used to evaluate the parameters!!!



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


import random
import logging

import deap.algorithms
import deap.tools
import pickle

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
        mdb_run=None,
        continue_cp=False,
		mdb = None):
    r"""This is the :math:`(~\alpha,\mu~,~\lambda)` evolutionary algorithm
    Args:
        population(list of deap Individuals)
        toolbox(deap Toolbox)
        mu(int): Total parent population size of EA
        cxpb(float): Crossover probability
        mutpb(float): Mutation probability
        ngen(int): Total number of generation to run
        stats(deap.tools.Statistics): generation of statistics
        halloffame(deap.tools.HallOfFame): hall of fame
        cp_frequency(int): generations between checkpoints
        cp_filename(ModelDataBase or None): mdb_run, where the checkpoint is stored in [generation]_checlpoint. Was: path to checkpoint filename
        continue_cp(bool): whether to continue
    """
    # added by arco
    if mdb_run is not None:
        assert isinstance(mdb_run, I.ModelDataBase) # mdb_run
    assert(halloffame is None)
    # end added by arco

    if continue_cp:
        # A file name has been given, then load the data from the file
        key = '{}_checkpoint'.format(get_max_generation(mdb_run))
        cp = mdb_run[key] #pickle.load(open(cp_filename, "r"))
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

        if mdb is not None:
            I.utils.wait_until_key_removed(mdb, 'pause')

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

        if(mdb_run and cp_frequency and
           gen % cp_frequency == 0):
            cp = dict(population=population,
                      generation=gen,
                      parents=parents,
                      halloffame=None, #halloffame, // arco
                      history=None, # history, // arco
                      logbook=None, # logbook, // arco
                      rndstate=random.getstate())
            # save checkpoint in mdb
            mdb_run.setitem('{}_checkpoint'.format(gen), cp, dumper = I.dumper_to_pickle)
            #pickle.dump(cp, open(cp_filename, "wb"))
            #logger.debug('Wrote checkpoint to %s', cp_filename)    
            
        if 'satisfactory' in mdb.keys():
            break

    return population #, logbook, history

####################################################
# end taken from bluepyopt
#####################################################

def run(self,
            max_ngen=10,
            offspring_size=None,
            continue_cp=False,
            cp_filename=None,
            cp_frequency=1,
            pop = None,
            mdb = None):
    
    """Copy pasted from the BluePyOpt package, however extended, such that a start population can be defined.
    Note: the population needs to be in a special format. Use methods in biophysics_fitting.population 
    to create a population."""
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
        assert (continue_cp == False)

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
        stats=None, # arco
        halloffame= None, # self.hof,
        cp_frequency=cp_frequency,
        continue_cp=continue_cp,
        cp_filename=cp_filename,
        mdb = mdb)

    return pop

def get_population_with_different_n_objectives(old_pop, n_objectives):
    '''function to adapt the number of objectives of individuals'''
    pop = []
    for p in old_pop:
        ind = WSListIndividual(p, obj_size = n_objectives)
        pop.append(ind)
    return pop
	
def start_run(mdb_setup, n, pop = None, client = None, continue_cp = False, offspring_size=1000, 
              eta=10, mutpb=0.3, cxpb=0.7, max_ngen = 600, satisfactory_boundary_dict = None):
    '''function to start an optimization run as specified in mdb_setup. The following attributes need
    to be defined in mdb_setup:
    
    - params ... this is a pandas.DataFrame with the parameternames as index and the columns min_ and max_
    - get_Simulator ... function, that returns a biophysics_fitting.simulator.Simulator object
    - get_Evaluator ... function, that returns a biophysics_fitting.evaluator.Evaluator object.
    - get_Combiner ... function, that returns a biophysics_fitting.combiner.Combiner object
    
    get_Simulator, get_Evaluator, get_Combiner accept the mdb_setup model_data_base as argument.
    
    This allows, that e.g. the Simular can depend on the model_data_base. Therefore it is e.g. possible, 
    that the path to the morphology is not saved as absolute path. Instead, fixed parameters can be
    updated accordingly.
    
    For an exemplary setup of a Simulaotr, Evaluator and Combiner object, see 
    biophysics_fitting.hay_complete_default_setup.
    
    For on examplary setup of a complete optimization project see 
    20190111_fitting_CDK_morphologies_Kv3_1_slope_step.ipynb
    
    You can also have a look at the test case in test_biophysics_fitting.test_optimizer.py
    
    satisfactory_boundary_dict needs to be given if you want to stop the optimisation when 
    a satisfactory models is found. Keys need to match the combined objectives. 
    '''
    # CAVE! get_mymap is doing more, than just to return a map function.
    # - the map function ignores the first argument. 
    #   The first argument (i.e. the function to be mapped on the iterable) is ignored.
    #   Instead, that function is hardcoded. It is defined in mdb_setup['get_Evaluator']
    #   This was neccessary, as my_ibea_evaluator and the deap individuals were causing pickle errors
    # - mymap also saves the features. As the bluepyopt optimizer only sees the sumarized 
    #   features (maximum of several individual features, see Hay et. al.), mymap is the ideal 
    #   place to insert a routine that saves all features before they get sumarized.
    # - mymap also creates a sub mdb in mdb_setup. The name of the sub_mdb is specified by n: It is str(n)
    #   mdb_setup[str(n)] then contains all the saved results

    mdb_run = setup_mdb_run(mdb_setup, n)
    mymap = get_mymap(mdb_setup, n, client, satisfactory_boundary_dict = satisfactory_boundary_dict)
    len_objectives = len(mdb_setup['get_Combiner'](mdb_setup).setup.names)
    parameter_df = mdb_setup['params']
    evaluator_fun = mdb_setup['get_Evaluator'](mdb_setup)
    evaluator = my_ibea_evaluator(parameter_df, len_objectives)
    opt = bpop.optimisations.DEAPOptimisation(evaluator, offspring_size=offspring_size,                                                                                                                                            
                                              eta=eta, mutpb=mutpb, cxpb=cxpb, 
                                              map_function = get_mymap(mdb_setup, mdb_run, client, satisfactory_boundary_dict = satisfactory_boundary_dict), 
                                              seed=n)
    
    if continue_cp == True:
        # if we want to continue a preexisting optimization, no population may be provided
        # also check, whether the optimization really exists
        assert(pop is None)
        if not str(n) in list(mdb_setup.keys()):
            raise ValueError('run {} is not in mdb_setup. Nothing to continue'.format(n))
    if continue_cp == False:
        # if we want to start a new optimization, ckeck that there is not an old optimizatation
        # that would be overwritten.
        if get_max_generation(mdb_run) > 0:
            raise ValueError('for n = {}, an optimization is already in mdb_setup. Either choose continue_cp=True or delete the optimization.'.format(n))
        if pop is not None:
            # if population is provided, make sure it fits the number of objectives of the current optimization
            print(("recreating provided population with a number of objectives of {}".format(len_objectives)))
            pop = get_population_with_different_n_objectives(pop, len_objectives)
        else: 
            # else generate a new population
            pop = opt.toolbox.population(n=offspring_size)    
    
    print(('starting multi objective optimization with {} objectives and {} parameters'.format(len_objectives, len(parameter_df))))    
    
    pop = eaAlphaMuPlusLambdaCheckpoint(
        pop,
        opt.toolbox,
        offspring_size,
        opt.cxpb,
        opt.mutpb,
        max_ngen,
        stats=None, # arco
        halloffame= None, # self.hof,
        cp_frequency=1,
        continue_cp=continue_cp,
        mdb_run=mdb_run,
        mdb = mdb_setup)

    return pop
    
    pop = run(opt, 
                           max_ngen=max_ngen, 
                           cp_filename = mdb_run, continue_cp=continue_cp,
                           pop = pop, mdb = mdb_setup)
    return pop
