"""Perofrm a random walk through parameter space starting from a seed point.

This module provides the :py:class:`~biophysics_fitting.exploration_from_seedpoint.RW` class,
which implements a random walk procedure through parameter space.
Every random parameter iteration provides new biophsyical parameters, 
which are evaluated by running a set of stimulus protocols with early stopping criteria.
"""


from functools import partial
import os
import pandas as pd
import numpy as np
import cloudpickle
import shutil
from .utils import get_vector_norm, convert_all_check_columns_bool_to_float
from .RW_analysis import read_pickle
from data_base.utils import silence_stdout
import time
import sys
import math
import glob
from config.isf_logging import logger


class RW:
    """
    Class to perform RW exploration from a seedpoint.
    
    Attributes:
        df_seeds (pd.DataFrame): individual seed points as rows and the parameters as columns
        param_ranges (pd.DataFrame): parameters as rows and has a ``min_`` and ``max_`` column denoting range of values this parameter may take
        params_to_explore (list): list of parameters that should be explored. If None, all parameters are explored.
        evaluation_function (Callable): 
            Function use to evaluate a vector of biphysical parameters.
            Must take one argument (a parameter vector) and return a tuple of  ``(inside, evaluation)``:
        
            - inside: boolean that indicates if the parameter vector is within experimental constraits
                (i.e. results in acceptable physiology) or not.
            - evaluation: dictionary that will be saved alongside the parameters. For example, this should contain
                ephys features.

            This function is usually :py:meth:`~biophysics_fitting.exploration_from_seedpoint.utils.evaluation_function_incremental_helper`.
        
        MAIN_DIRECTORY (str): output directory in which results are stored.
        min_step_size (float): minimum step size for the random walk
        max_step_size (float): maximum step size for the random walk
        checkpoint_every (int): save the results every n iterations
        checkpoint_by_time (float): time interval in minutes for checkpointing for using time-based checkpointing. If both
            checkpoint_every and checkpoint_by_time are set, checkpointing will be done by time.
        concat_every_n_save (int): number of checkpoints after which the pickle files are concatenated and cleaned
        n_iterations (int): number of iterations to run the random walk
        mode (str): Random walk mode. Options: (None, 'expand'). default: None
            'expand': only propose new points that move further away from seedpoint
        aim_params (dict): this param will make the exploration algorithm propose only new points such that a set of
            parameters aims certain values during exploration.
            Default: {}
        stop_n_inside_with_aim_params (int): number of successful models / set of parameters inside space with aim_params
            to find before stopping exploration
        normalized_aim_params (pd.Series): normalized aim parameters
    """
    def __init__(self, df_seeds = None, param_ranges = None, 
                params_to_explore = None, evaluation_function = None, 
                MAIN_DIRECTORY = None, min_step_size = 0, max_step_size = 0.02, 
                checkpoint_every = 100, checkpoint_by_time = None, 
                concat_every_n_save = 60, n_iterations = 60000,
                mode = None, aim_params=None, stop_n_inside_with_aim_params = -1):
        '''
        Args:
            df_seeds (pd.DataFrame): individual seed points as rows and the parameters as columns
            param_ranges (pd.DataFrame): parameters as rows and has a ``min_`` and ``max_`` column denoting range of values this parameter may take
            params_to_explore (list): list of parameters that should be explored. If None, all parameters are explored.
            evaluation_function (Callable): 
                takes one argument (a new parameter vector) and returns:

                - inside: boolean that indicates if the parameter vector is within experimental constraits (i.e. results in acceptable physiology) or not. 
                - evaluation: dictionary that will be saved alongside the parameters. For example, this should contain ephys features.

            checkpoint_every (int): save the results every n iterations
            check_point_by_time (float): time interval in minutes for checkpointing for using time-based checkpointing. If both
                checkpoint_every and checkpoint_by_time are set, checkpointing will be done by time.
            concat_every_n_save (int): number of checkpoints after which the intermediate ``.pickle` files are concatenated to a single ``.parquet`` dataframe.
            mode (str): Random walk mode. Options: (None, 'expand'). default: None
                'expand': only propose new points that move further away from seedpoint
            aim_params (dict): this param will make the exploration algorithm propose only new points such that a set of 
                parameters aims certain values during exploration.
                Default: {}
            stop_n_inside_with_aim_params (int): number of successful models / set of parameters inside space with aim_params 
                to find before stopping exploration
            MAIN_DIRECTORY (str): output directory in which results are stored.
        '''
        self.df_seeds = df_seeds
        self.param_ranges = param_ranges
        self.MAIN_DIRECTORY = MAIN_DIRECTORY
        self.evaluation_function = evaluation_function
        self.min_step_size = min_step_size
        self.max_step_size = max_step_size
        self.checkpoint_every = checkpoint_every
        self.checkpoint_by_time = checkpoint_by_time
        self.concat_every_n_save = concat_every_n_save
        self.all_param_names = list(self.param_ranges.index)
        self.n_iterations = n_iterations
        self.mode = mode
        if params_to_explore is None:
            self.params_to_explore = self.all_param_names
        else:
            self.params_to_explore = params_to_explore
        if aim_params is None: self.aim_params = {}
        else: self.aim_params = aim_params
        self.normalized_aim_params = self._normalize_aim_params(aim_params)
        self.stop_n_inside_with_aim_params = stop_n_inside_with_aim_params
    
    def _normalize_aim_params(self,aim_params):
        """Normalize aim parameters to be between 0 and 1.
        
        Args:
            aim_params (dict): aim parameters
            
        Returns:
            pd.Series: normalized aim parameters
        """
        normalized_params = pd.Series(aim_params)
        for key in normalized_params.keys():
            min_ = self.param_ranges['min'][key]
            max_ = self.param_ranges['max'][key]
            normalized_params[key] = (normalized_params[key]-min_)/(max_-min_)
        return normalized_params
    
    def _normalize_params(self,p):
        """Normalize parameters to be between 0 and 1.
        
        Args:
            p (pd.Series): parameter vector
            
        Returns:
            pd.Series: normalized parameter vector"""
        assert(isinstance(p,pd.Series))
        assert(len(p) == len(self.all_param_names))
        min_ = self.param_ranges['min']
        max_ = self.param_ranges['max']
        return (p-min_)/(max_-min_)
    
    def _unnormalize_params(self, p):
        """Unnormalize parameters to be between min and max.
        
        Args:
            p (pd.Series): normalized parameter vector
            
        Returns:
            pd.Series: unnormalized parameter vector"""
        assert(isinstance(p,pd.Series))
        assert(len(p) == len(self.all_param_names))
        min_ = self.param_ranges['min']
        max_ = self.param_ranges['max']
        return p*(max_-min_)+min_
        
    def _concatenate_and_clean(self,seed_folder, particle_id, iteration  = None): 
        """Concatenate the intermediate ``.pickle`` results and save as one parquet file. 
        
        Removes the pickle files.
        
        Args:
            seed_folder (str): folder where the seedpoint is located
            particle_id (int): id of the particle
            iteration (int): iteration number. Default: None
        """
        # check that we are doing this for the latest iteration
        outdir = os.path.join(seed_folder, str(particle_id))
        iterations = sorted(list(set([int(f.split('.')[0]) for f in os.listdir(outdir)
                      if f.endswith('.pickle') or f.endswith('.parquet')])), reverse=True)
        pickle_files = [f for f in os.listdir(outdir) if f.endswith('.pickle')]
        iteration = iterations[0]
        
        df_parquet_path = os.path.join(outdir, f'{iteration}.parquet')
        if os.path.isfile(df_parquet_path): 
            logger.warning(f'Parquet file already exists {df_parquet_path}')
            self._clean_the_pickles(outdir, pickle_files, iteration) 
            return 

        df = read_pickle(seed_folder, particle_id)
        df = convert_all_check_columns_bool_to_float(df)
        df.to_parquet(df_parquet_path + '.saving')
        shutil.move(df_parquet_path + '.saving', df_parquet_path) 
        self._clean_the_pickles(outdir, pickle_files, iteration) 

    def _clean_the_pickles(self,outdir, files, iteration):
        """Remove the pickle files that correspond to the intermediate results of a iteration.
        
        Args:
            outdir (str): directory where the pickle files are located
            files (list): list of files in the directory
            iteration (int): iteration number
        """
        paths = [os.path.join(outdir, file) for file in files]
        logger.info(f'Cleaning the pickle files in {outdir}')
        for path in paths: 
            os.remove(path)
            if not path.endswith(f'{iteration}.pickle'): # do not remove the last rngn
                os.remove(path + '.rngn')

    def _load_pickle_or_parquet(self,outdir, iteration, mode = 'parquet_load'):
        """Load the results of a iteration from a pickle or parquet file.
        
        Args:
            outdir (str): directory where the pickle or parquet files are located
            iteration (int): iteration number
            mode (str): mode to load the results. Default: 'parquet_load'
            
        Returns:
            tuple: dataframe and path to the file
        """
        assert mode in ['pickle_load', 'parquet_load'], 'mode must be "pickle_load" or "parquet_load"'
        if mode == 'pickle_load': 
            df_path = os.path.join(outdir, '{}.pickle'.format(iteration))
            df = pd.read_pickle(df_path)   
        if mode == 'parquet_load':
            df_path = os.path.join(outdir, '{}.parquet'.format(iteration))
            df = pd.read_parquet(df_path)
        return df, df_path

        
    def assess_aim_params_reached(self, normalized_params, tolerance=1e-4):
        """Check whether the aim parameters have been reached.
        
        For each parameter in the aim_params dictionary, check whether the parameter has been reached.
        A parameter is reached if it lies within a certain tolerance of the aim parameter.
        
        Args:
            normalized_params (np.array): normalized parameter vector
            tolerance (float): tolerance for the aim parameters to be reached. Default: 1e-4
            
        Returns:
            list: boolean values indicating whether each aim parameter has been reached or not.
        """
        reached_aim_params = []
        for key in self.aim_params.keys():
            idx = self.params_to_explore.index(key)
            reached_aim_params.append(math.isclose(normalized_params[idx],self.normalized_aim_params[key], abs_tol=tolerance))
        return reached_aim_params
        
    def run_RW(self, selected_seedpoint, particle_id, seed = None):
        """Run random walk exploration from a seed point.
        
        Args:
            selected_seedpoint (int): index of the seed point in df_seeds
            particle_id (int): id of the particle
            seed (int): random seed for the random number generator
            
        Returns:
            None. Saves the results to :paramref:`MAIN_DIRECTORY`/:paramref:`selected_seedpoint`/:paramref:`particle_id`
        """
        try: # to not cause an error in pickles created before mode was added
            self.mode
        except AttributeError as e:
            self.mode = None
        # get the parameters of the seed point (there might be more info in df_seeds than just the parameters)
        seed_point_for_exploration_pd = self.df_seeds[self.params_to_explore].iloc[selected_seedpoint]
        logger.info(len(seed_point_for_exploration_pd)) # this is the point in space to start exploring
        # normalize seed point parameters
        seed_point_for_exploration_normalized_pd = self._normalize_params(seed_point_for_exploration_pd)
        seed_point_for_exploration_normalized_selected_np = seed_point_for_exploration_normalized_pd[self.params_to_explore].values
        
        # set seed
        assert(seed is not None)
        np.random.seed(seed)    
        
        # set up folder structure
        logger.info('My random number generator seed is', seed)
        SEED_DIR = os.path.join(self.MAIN_DIRECTORY, str(selected_seedpoint))
        OPERATION_DIR = os.path.join(SEED_DIR, str(particle_id))
        if not os.path.exists(OPERATION_DIR):
            os.makedirs(OPERATION_DIR)
        logger.info('I am particle', particle_id, 'and I write to', OPERATION_DIR)
        
        # check if we start from scratch or if we resume an exploration
        file_list = os.listdir(OPERATION_DIR) #newnewnew
        iterations = list(set([int(f.split('.')[0]) for f in file_list 
                    if f.endswith('.pickle') or f.endswith('.parquet')])) #set to list to drop duplicates
        iterations = sorted(iterations,reverse=True)
        if iterations and max(iterations) > self.n_iterations:
            logger.info('Max iterations reached. exit gracefully')
            return 
            #sys.exit(0)
        if len(iterations) == 0:
            logger.info('So far nothing simulated, start from seedpoint', selected_seedpoint)
            p = seed_point_for_exploration_pd # p is pandas and the full vector and unnormalized
            iteration = 0
            inside, initial_evaluation = self.evaluation_function(p) # inside determines if the evaluation has been successful or not
            assert(inside)
            initial_evaluation['inside'] = inside
            out = [initial_evaluation]  # out is what will be saved
            save_count = 0 #newnewnew
        else:
            # we resume the exploration. check how to load the saved files
            save_count = len([f for f in file_list if f.endswith('.pickle')])  #count pickle files 
            parquet_count =  len([f for f in file_list if f.endswith('.parquet')])
            load_mode = None 
            if parquet_count == 0: 
                load_mode = 'pickle_load'
            elif save_count == 0:
                load_mode = 'parquet_load' 
            else: #there are both pickle and parquet files
                #check: last iteration is not saved in both a pickle and parquet file
                if os.path.isfile(os.path.join(OPERATION_DIR, '{}.parquet'.format(iterations[0]))):
                    self._concatenate_and_clean()
                    save_count = 0
                    load_mode = 'parquet_load' 
                # first load the pickles, then the parquet
                load_list = ['pickle_load']*save_count + ['parquet_load']*parquet_count

            # search for last model inside the space, starting from the iteration saved the latest
            for i, iteration in enumerate(iterations):
                if not load_mode: 
                    df, df_path = self._load_pickle_or_parquet(OPERATION_DIR,iteration,load_list[i])
                else: 
                    df, df_path = self._load_pickle_or_parquet(OPERATION_DIR,iteration,load_mode)

                logger.info('Found preexisting RW, continue from there. Iteration', iteration)
                logger.info('Loaded file', df_path) 
                df = df[df.inside]
                try:
                    p = df.iloc[-1][self.all_param_names] # p is pandas and the full vector and unnormalized
                    break
                except IndexError:
                    logger.info("didn't find a model inside the space, try previous iteration")

            # set the random number generator to the latest state
            assert(max(iterations) == iterations[0])
            rngn_path = os.path.join(OPERATION_DIR, '{}.pickle.rngn'.format(iterations[0]))
            with open(rngn_path, 'rb') as f:
                rngn = cloudpickle.load(f)
            logger.info('set state of random number generator')
            np.random.set_state(rngn)
            
            # set current iteration to follow up on the latest saved iteration
            iteration = iterations[0] + 1
            out = [] # out is what is saved 
        
        p_normalized = self._normalize_params(p)
        p_normalized_selected_np = p_normalized[self.params_to_explore].values
        reached_aim_params = self.assess_aim_params_reached(p_normalized)
        
        # exploration loop
        logger.info('exploration loop')
        save_time = time.time()
        save = False
        while True:
            logger.info('New loop. Current iteration', iteration)
            if self.checkpoint_by_time: 
                current_time = time.time()
                time_since_last_save = (current_time - save_time)/60 #in minutes
                if time_since_last_save>self.checkpoint_by_time and len(out) > 0:
                    logger.info(f'It\'s been {time_since_last_save} minutes since last checkpoint. Saving!')
                    save = True
                    save_time = current_time
            
            elif iteration % self.checkpoint_every == 0 and iteration > 0:
                logger.info('Saving')
                save = True 
                
            if save: 
                df_path = os.path.join(OPERATION_DIR, '{}.pickle'.format(iteration))
                df = pd.DataFrame(out)
                df.to_pickle(df_path + '.saving')
                with open(df_path + '.rngn', 'wb') as f:
                    cloudpickle.dump(np.random.get_state(), f)  
                # deal with the case that exploration was interupted while saving the dataframe
                shutil.move(df_path + '.saving', df_path) 
                out = [] # reset output after saving
                save = False
                save_count += 1        

            if save_count != 0 and save_count % self.concat_every_n_save == 0:
                logger.info(f'{save_count} saved pickle files. Concatenating and saving as parquet.')
                self._concatenate_and_clean(SEED_DIR, particle_id, iteration)
                save_count = 0
                
            # this inner loop suggests new movements until the suggested step is within bounds
            # Here we enforce the algorithm to run in the specified mode (once we make the suggested particle move
            # according to the mode mode_fulfilled becomes true), and also the aim params are forced to move in 
            # the right direction to reach the aim values (unidir_params_fulfilled becomes true).
            # If we've enforced both things, the while stops, as we have the desired movement.
            logger.info('Get new position')    
            n_suggestion = 0  
            dist = get_vector_norm(p_normalized_selected_np-seed_point_for_exploration_normalized_selected_np)
            mode_fulfilled = False
            unidir_params_fulfilled = False
            while not mode_fulfilled or not unidir_params_fulfilled:
                n_suggestion += 1
                movement = np.random.randn(len(self.params_to_explore))

                # Ensure that the movement is in the right direction for the aim parameters,
                # or that they do not move if they reached their aim value
                for aim_param, reached_aim_param in zip(self.aim_params.keys(),reached_aim_params):
                    idx = self.params_to_explore.index(aim_param)
                    if reached_aim_param:
                        movement[idx] = 0
                    else:
                        positive_movement = (self.aim_params[aim_param]-seed_point_for_exploration_pd[aim_param])>0
                        if positive_movement:
                            movement[idx] = abs(movement[idx])
                        else:
                            movement[idx] = -abs(movement[idx])
                        
                movement = movement/get_vector_norm(movement)
                #sample step size from a normal distribution
                step_size = np.random.rand()*(self.max_step_size-self.min_step_size)+self.min_step_size
                movement = movement * step_size
                        
                p_proposal = p_normalized_selected_np + movement
                if p_proposal.max() <= 1 and p_proposal.min() >= 0:
                    if self.mode is None:
                        mode_fulfilled = True
                    elif self.mode == 'expand':
                        delta_dist = get_vector_norm(p_proposal-seed_point_for_exploration_normalized_selected_np) - dist
                        if delta_dist > 0:
                            logger.info('new position increases distance by {}'.format(delta_dist))
                            mode_fulfilled = True
                    else:
                        raise ValueError('mode must be None or "expand"')
                    
                    if len(self.normalized_aim_params.keys()) == 0:
                        unidir_params_fulfilled = True
                    else:
                        right_direction = []
                        for i,key in enumerate(self.normalized_aim_params.keys()):
                            idx = self.params_to_explore.index(key)
                            previous_dist = abs(p_normalized_selected_np[idx]-self.normalized_aim_params[key])
                            current_dist = abs(p_proposal[idx]-self.normalized_aim_params[key])
                            if current_dist<previous_dist or reached_aim_params[i]:
                                right_direction.append(True)
                            else:
                                right_direction.append(False)
                        if all(right_direction):
                            unidir_params_fulfilled = True
                    
            logger.info('Position within boundaries found, step size is', step_size, 
                'Tested ', n_suggestion, 'positions to find one inside the box.') 
            # homogenize parameter representation
            # note p_proposal is normalized and numpy
            # p is pandas and the full vector and unnormalized
            p = seed_point_for_exploration_normalized_pd.copy()
            p[self.params_to_explore] = p_proposal
            p_normalized = p.copy()
            p = self._unnormalize_params(p)

            # evaluate new point
            inside, evaluation = self.evaluation_function(p)
            logger.info('Inside the space?', inside)
            evaluation['n_suggestion'] = n_suggestion
            evaluation['inside'] = inside
            out.append(evaluation)
            if inside:
                for key in self.normalized_aim_params.keys():
                    idx = self.params_to_explore.index(key)
                    logger.info(key,' (normalized) - current: ', p_normalized_selected_np[idx], ', proposed: ', p_normalized[key])
                logger.info('Moving current position to proposed position')
                p_normalized_selected_np = p_proposal
                logger.info('distance to initial seed point (normalized):', get_vector_norm(p_normalized_selected_np-seed_point_for_exploration_normalized_selected_np))
                reached_aim_params = self.assess_aim_params_reached(p_normalized)
                if all(reached_aim_params) and len(reached_aim_params)!=0:
                    logger.info('Reached all aim parameters! Creating flag in seedpoint directory...')
                    seedpoint_dir = os.path.join(self.MAIN_DIRECTORY, '{}'.format(selected_seedpoint))
                    aim_params_inside_flag = glob.glob(os.path.join(seedpoint_dir,'aim_params_successful_model_*'))
                    if len(aim_params_inside_flag) == 0:
                        open(os.path.join(seedpoint_dir,'aim_params_successful_model_1'), 'a').close()
                        count = 1
                    else:
                        count = int(aim_params_inside_flag[0].split('_')[-1])
                        count+=1
                        os.rename(aim_params_inside_flag[0], os.path.join(seedpoint_dir,'aim_params_successful_model_{}'.format(count)))
                    if count == self.stop_n_inside_with_aim_params:
                        logger.info('Reached aim params {} times for successful models. Exit gracefully'.format(count))
                        break
            iteration += 1