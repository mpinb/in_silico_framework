# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Perform a random walk through parameter space starting from a seed point.

This module provides the :class:`~biophysics_fitting.exploration_from_seedpoint.RW` class,
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
import time
import sys
import math
import glob
from typing import Literal
from .utils import get_vector_norm, convert_all_check_columns_bool_to_float
from .RW_analysis import read_pickle
import logging
logger = logging.getLogger("ISF").getChild(__name__)


class RW:
    """Class to perform RW exploration from a seedpoint.
    
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

            This function is usually :func:`~biophysics_fitting.exploration_from_seedpoint.utils.evaluation_function_incremental_helper`.
        
        MAIN_DIRECTORY (str): output directory in which results are stored.
        min_step_size (float): minimum step size for the random walk
        max_step_size (float): maximum step size for the random walk
        checkpoint_every (int): save the results every n iterations
        checkpoint_by_time (float): time interval in minutes for checkpointing for using time-based checkpointing. If both
            checkpoint_every and checkpoint_by_time are set, checkpointing will be done by time.
        n_iterations (int): number of iterations to run the random walk
        mode (str): Random walk mode. Options: (None, 'expand', 'custom'). default: None
            'expand': only propose new points that move further away from seedpoint
            'custom': use custom conditions to propose new points. If this mode is used, mode_condition_fun must be provided to evaluate the new points.
        mode_condition_fun (Callable): 
            Function that takes a parameter vector and returns a boolean indicating whether the point is acceptable or not.
            This function is used in 'custom' mode to propose new points.
        aim_params (dict): this param will make the exploration algorithm propose only new points such that a set of
            parameters aims certain values during exploration.
            Default: {}
        stop_n_inside_with_aim_params (int): number of successful models / set of parameters inside space with aim_params
            to find before stopping exploration
        normalized_aim_params (pd.Series): normalized aim parameters
    """
    def __init__(
        self, 
        df_seeds = None, 
        param_ranges = None, 
        params_to_explore = None, 
        evaluation_function = None, 
        MAIN_DIRECTORY = None, 
        min_step_size = 0, 
        max_step_size = 0.02, 
        checkpoint_every = 100, 
        checkpoint_by_time = None, 
        n_iterations = 60000,
        mode = None, 
        mode_condition_fun = None,
        aim_params=None, 
        stop_n_inside_with_aim_params = -1):
        '''
        Args:
            df_seeds (pd.DataFrame): individual seed points as rows and the parameters as columns
            param_ranges (pd.DataFrame): parameters as rows and has a ``min_`` and ``max_`` column denoting range of values this parameter may take
            params_to_explore (list): list of parameters that should be explored. If None, all parameters are explored.
            evaluation_function (Callable): 
                takes one argument (a new parameter vector) and returns:
                - inside: boolean that indicates if the parameter vector is within experimental constraits (i.e. results in acceptable physiology) or not. 
                - evaluation: dictionary that will be saved alongside the parameters. For example, this should contain ephys features.
            checkpoint_every (int): iteration interval at which the results are saved e.i., n for checkpointing every n iterations. If both 
                checkpoint_every and checkpoint_by_time are set, checkpointing will be done by time.
            check_point_by_time (float): time interval (in minutes) at which results are saved e.i., n for checkpointing every n minutes. If both
                checkpoint_every and checkpoint_by_time are set, checkpointing will be done by time.
            mode (str): Random walk mode. Options: (None, 'expand', 'custom'). If none, no additional constraints will be considered when proposing new points.
                'expand': only propose new points that move further away from seedpoint
                'custom': use custom conditions to propose new points. If this mode is used, mode_condition_fun must be provided to evaluate the new points.
                Default: None
            mode_condition_fun (Callable): 
                A function that takes a parameter vector and returns a boolean indicating if the proposed point 
                is acceptable. Used if mode is set to custom. 
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
        self.all_param_names = self.param_ranges.index
        self.n_iterations = n_iterations
        self.mode = mode
        self.mode_condition_fun = mode_condition_fun
        self.params_to_explore = params_to_explore or self.all_param_names
        if aim_params is None: self.aim_params = {}
        else: self.aim_params = aim_params
        self.normalized_aim_params = self._normalize_aim_params(aim_params)
        self.stop_n_inside_with_aim_params = stop_n_inside_with_aim_params
    
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
    
    def _ensure_direction_toward_aim(self, movement, reached_aim_params, seed_pt_pd):
        """Ensure that the movement is in the right direction for the aim parameters, 
        or that there is no movement if aim value is reached.

        Args:
            movement (np.array): movement vector to adjust
            reached_aim_params (list): list of booleans indicating whether each aim parameter has been reached or not.
            seed_point (pd.Series): seed point parameters
        
        Returns:
            np.array: adjusted movement vector
        """
        for aim_param, reached in zip(self.aim_params.keys(), reached_aim_params):
            idx = self.params_to_explore.index(aim_param)
            if reached:
                movement[idx] = 0
            else:
                direction = 1 if (self.aim_params[aim_param]- seed_pt_pd[aim_param])>0 else -1
                movement[idx] = abs(movement[idx]) * direction
        return movement

    def _check_movement_towards_aim(self, current_np, proposal):
        """
        Check if the proposed parameters are closer to the aim parameters than the current parameters.

        Args:
            current_np (np.array): current normalized parameters
            proposal (np.array): proposed normalized parameters
        
        Returns:
            bool: True if the proposed parameters are closer to the aim parameters, False otherwise.
        """
        for key in self.aim_params:
            idx = self.params_to_explore.index(key)
            prev_dist = abs(current_np[idx] - self.normalized_aim_params[key])
            new_dist = abs(proposal[idx] - self.normalized_aim_params[key])
            if new_dist >= prev_dist:
                return False
        return True

    def _flag_aim_params_success(self, seed_dir):
        """Create a flag in the seedpoint directory to indicate that aim parameters have been reached
        or adjust the flag to indicate how many times the aim parameters have been reached.

        Args:
            seed_dir (str): directory where the seedpoint is located
       
        Returns:
            int: count of how many times the aim parameters have been reached
        """
        flag = glob.glob(os.path.join(seed_dir, 'aim_params_successful_model_*'))
        count = int(flag[0].split('_')[-1]) + 1 if flag else 1
        new_flag = os.path.join(seed_dir, f'aim_params_successful_model_{count}')
        if flag:
            os.rename(flag[0], new_flag)
        else:
            open(new_flag, 'a').close()
        return count

    def _save_checkpoint(self, iteration, out, op_dir):
        """Save the results saved in "out" to a pickle file.
        Additionally, save the state of the random number generator.

        Args:
            iteration (int): current iteration number
            out (list): list of dictionaries containing the evaluation results for each parameter vector
            op_dir (str): directory where the results are saved

        Returns:
            None. Saves the results to a pickle file in the specified directory.
        """
        path = os.path.join(op_dir, f'{iteration}.pickle')
        pd.concat(out).to_pickle(path + '.saving')
        logger.info('Checkpointing')
        with open(path + '.rngn', 'wb') as f:
            cloudpickle.dump(np.random.get_state(), f)
        shutil.move(path + '.saving', path)

    def _propose_new_position(self, p_normalized_np, seed_normalized_np, dist, reached_aim_params, seed_pt_pd):
        """Propose a new position to move to in the parameter space. 
        If applicable, the new position is proposed according to the mode and aim parameters.

        Args:
            p_normalized_np (np.array): normalized parameter vector of the current position
            seed_normalized_np (np.array): normalized parameter vector of the seed point
            dist (float): distance from the seed point to the current position
            reached_aim_params (list): list of booleans indicating whether each aim parameter has been reached or not.
            seed_pt_pd (pd.Series): seed point parameters

        Attention:
            :param:`p_normalized_np` and :param:`seed_normalized_np` do not necessarily need to include parameters that are not actively being explored. 
            However, they may, since frozen parameters do not contribute to the distance. 
            Both arguments simply need to be consistent about including or not including parameters that aren't explored.

        Returns:
            tuple: proposed position (np.array) and number of suggestions it took to find an acceptable position (int)        
        """
        if self.mode not in [None, 'expand', 'custom']: 
            raise ValueError('Mode must be None, "expand" or "custom"') 
        n_suggestion = 0
        mode_fulfilled = False
        while not mode_fulfilled:
            n_suggestion += 1
            movement = np.random.randn(len(self.params_to_explore))
            movement = self._ensure_direction_toward_aim(movement, reached_aim_params, seed_pt_pd)
            movement /= get_vector_norm(movement)
            step_size = np.random.rand() * (self.max_step_size - self.min_step_size) + self.min_step_size
            movement *= step_size
            p_proposal = p_normalized_np + movement
            if p_proposal.max() > 1 or p_proposal.min() < 0:
                continue
            if self.mode is None:
                mode_fulfilled = True
            elif (self.mode == 'expand' and 
                get_vector_norm(p_proposal - seed_normalized_np) - dist > 0):
                mode_fulfilled = True
            elif self.mode == 'custom':
                if self.mode_condition_fun is None:
                    raise ValueError('mode_condition_fun must be provided in "custom" mode')
                mode_fulfilled = self.mode_condition_fun(p_proposal)
            if len(self.normalized_aim_params.keys()) > 0 and not self._check_movement_towards_aim(p_normalized_np, p_proposal):
                continue
            logger.info(f"Position within boundaries found, step size is {step_size}, Tested {n_suggestion} positions to find one.")
            return p_proposal, n_suggestion
        
    
    def _concatenate_and_clean(self, seed_folder, particle_id): 
        """Concatenate the intermediate ``.pickle`` results and save as one parquet file. 
        Removes the pickle files.
        
        Args:
            seed_folder (str): folder where the seedpoint is located
            particle_id (int): id of the particle
            iteration (int): iteration number. Default: None
        """
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

    def _load_pickle_or_parquet(self,outdir, iteration, mode: Literal['pickle', 'parquet']):
        """Load the results of a iteration from a pickle or parquet file.
        
        Args:
            outdir (str): directory where the pickle or parquet files are located
            iteration (int): iteration number
            mode (str): mode to load the results. Default: 'parquet_load'
            
        Returns:
            tuple: dataframe and path to the file
        """
        df_path = os.path.join(outdir, '.'.join([str(iteration), mode]))
        return getattr(pd, 'read_' + mode)(df_path), df_path

    def _load_existing_exploration(self, OPERATION_DIR, iteration_files, file_list):
        """Load the existing exploration results from the specified directory to continue the random walk.

        Args:
            OPERATION_DIR (str): directory where the results are stored
            iteration_files (list): list of iteration files
            file_list (list): list of files in the directory
        
        Returns:
            tuple: parameters of the last iteration, next iteration number, count of pickle files, and
            the state of the random number generator.
        """
        pickle_count = len([f for f in file_list if f.endswith('.pickle')])
        parquet_count = len([f for f in file_list if f.endswith('.parquet')])
        load_list = ['pickle'] * pickle_count + ['parquet'] * parquet_count
        for i, iteration in enumerate(iteration_files):
            df, df_path = self._load_pickle_or_parquet(OPERATION_DIR, iteration, load_list[i])
            logger.info(f'Loaded file {df_path}')
            df = df[df.inside]
            try:
                p = df.iloc[-1][self.all_param_names]
                break
            except IndexError:
                logger.info("Didn't find a model inside the space, trying previous iteration")
        assert max(iteration_files) == iteration_files[0]
        with open(os.path.join(OPERATION_DIR, f'{iteration_files[0]}.pickle.rngn'), 'rb') as f:
            rngn = cloudpickle.load(f)
        return p, iteration_files[0] + 1, pickle_count, rngn
    
    def run_RW(self, selected_seedpoint, particle_id, seed = None):
        """Run random walk exploration from a seed point.
        
        Args:
            selected_seedpoint (int): index of the seed point in df_seeds
            particle_id (int): id of the particle
            seed (int): random seed for the random number generator
            
        Returns:
            None. Saves the results to :attr:`MAIN_DIRECTORY`/:param:`selected_seedpoint`/:param:`particle_id`
        """
        try: # to not cause an error in pickles created before mode was added
            self.mode
        except AttributeError as e:
            self.mode = None
        # get the parameters of the seed point (there might be more info in df_seeds than just the parameters)
        seed_params_all_pd = self.df_seeds[self.all_param_names].iloc[selected_seedpoint]
        logger.info(str(len(seed_params_all_pd)))
        # normalize seed point parameters
        seed_params_all_normalized_pd = self._normalize_params(seed_params_all_pd)
        seed_params_expl_normalized_np = seed_params_all_normalized_pd[self.params_to_explore].values
        # set seed
        assert(seed is not None)
        np.random.seed(seed)
        logger.info(f'My random number generator seed is {seed}')

        # set up folder structure
        SEED_PT_DIR = os.path.join(self.MAIN_DIRECTORY, str(selected_seedpoint))
        OPERATION_DIR = os.path.join(SEED_PT_DIR, str(particle_id))
        os.makedirs(OPERATION_DIR, exist_ok=True)
        logger.info(f"I am particle  {particle_id}, and I write to {OPERATION_DIR}")

        concat_every = 60 #number of checkpoints after which the intermediate pickle files are concatenated to a single dataframe (".parquet")
        
        # check if we start from scratch or if we resume an exploration
        file_list = os.listdir(OPERATION_DIR)
        iteration_files = list(set([int(f.split('.')[0]) for f in file_list 
                                    if f.endswith('.pickle') or f.endswith('.parquet')])) #set to list to drop duplicates
        iteration_files = sorted(iteration_files,reverse=True)
        if iteration_files and max(iteration_files) > self.n_iterations:
            logger.info('Max iterations reached. Exiting gracefully')
            self._concatenate_and_clean(SEED_PT_DIR, particle_id)
            return 
        if len(iteration_files) == 0:
            logger.info(f"Starting fresh from seedpoint {selected_seedpoint}")
            p = seed_params_all_pd
            iteration = 0
            inside, initial_evaluation = self.evaluation_function(p)
            assert inside
            initial_evaluation['inside'] = inside
            out = [initial_evaluation]
            save_count = 0
        else:
            p, iteration, save_count, rngn = self._load_existing_exploration(OPERATION_DIR, iteration_files, file_list)
            logger.info(f'Found preexisting RW, continue from there. Iteration {iteration}')
            logger.info('set state of random number generator')
            np.random.set_state(rngn)
            out = []

        params_all_normalized = self._normalize_params(p)
        params_expl_normalized_np = params_all_normalized[self.params_to_explore].values
        reached_aim_params = self.assess_aim_params_reached(params_all_normalized)

        logger.info("Exploration loop")
        save_time = time.time()
        while True:
            logger.info(f"New loop. Current iteration {iteration}")
            if self.checkpoint_by_time: 
                since_last_save = (time.time() - save_time)/60 #in minutes
                if since_last_save>self.checkpoint_by_time and len(out) > 0:
                    logger.info(f'It\'s been {since_last_save} minutes since last checkpoint. Checkpointing.')
                    self._save_checkpoint(iteration, out, OPERATION_DIR)
                    save_time = time.time()
                    out = []
                    save_count += 1 
            elif iteration > 0 and iteration % self.checkpoint_every == 0:
                self._save_checkpoint(iteration, out, OPERATION_DIR)
                out = []
                save_count += 1 
            if save_count != 0 and save_count % concat_every == 0:
                self._concatenate_and_clean(SEED_PT_DIR, particle_id)
                save_count = 0

            dist = get_vector_norm(params_expl_normalized_np - seed_params_expl_normalized_np)
            params_expl_proposal, n_suggestion = self._propose_new_position(
                params_expl_normalized_np, 
                seed_params_expl_normalized_np, 
                dist, 
                reached_aim_params, 
                seed_params_all_pd
                )
            p = seed_params_all_normalized_pd.copy()
            p[self.params_to_explore] = params_expl_proposal
            params_all_normalized = p.copy()
            p = self._unnormalize_params(p)
            # evaluate new point
            inside, evaluation = self.evaluation_function(p)
            logger.info(f'Inside the space? {inside}')
            evaluation['n_suggestion'] = n_suggestion
            evaluation['inside'] = inside
            out.append(evaluation)
            if inside:
                params_expl_normalized_np = params_expl_proposal
                logger.info(f"Accepted new point. Distance from seed: {dist}")
                reached_aim_params = self.assess_aim_params_reached(params_all_normalized)
                if all(reached_aim_params) and reached_aim_params:
                    logger.info('Reached all aim parameters! Creating flag in seedpoint directory...')
                    count = self._flag_aim_params_success(SEED_PT_DIR)
                    if count == self.stop_n_inside_with_aim_params:
                        logger.info('Reached aim params {} times for successful models. Exit gracefully'.format(count))
                        return
                if iteration>self.n_iterations:
                    self._concatenate_and_clean(SEED_PT_DIR, particle_id)
                    logger.info('Max iterations reached. Exiting gracefully')
                    return 
            iteration += 1
