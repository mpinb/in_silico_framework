############################################################
# The code below is taken from bluepyopt.deapext.algorithms.py
# it is changed by @abast on 11/11/2018 such that the checkpoint only saves the population, but not the history
# and hall of fame, as this can be easily reconstructed from the data saved by mymap
# 
# Copyright (c) 2016, EPFL/Blue Brain Project
#  The code below is part of `BluePyOpt <https://github.com/BlueBrain/BluePyOpt>`_
#  This library is free software; you can redistribute it and/or modify it under
#  the terms of the GNU Lesser General Public License version 3.0 as published
#  by the Free Software Foundation.
#  This library is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
#  details.
#  You should have received a copy of the GNU Lesser General Public License
#  along with this library; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
############################################################
"""Optimisation class"""

# pylint: disable=R0914, R0912

import logging
import pickle
import random

import deap.algorithms
import deap.tools

from data_base.IO.LoaderDumper import to_pickle as dumper_to_pickle
from data_base.utils import wait_until_key_removed

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
        from data_base import is_data_base
        assert is_data_base(db_run.basedir)
        # assert db_run.__class__.__name__ in ("ModelDataBase", "ISFDataBase")  # db_run
    assert halloffame is None
    # --- end added by arco

    if continue_cp:
        # A file name has been given, then load the data from the file
        from .optimizer import get_max_generation  # lazy import to avoid circular dependency
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
