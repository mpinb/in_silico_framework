from functools import partial
import os
import pandas as pd
import numpy as np
import cloudpickle
import shutil
from .utils import get_vector_norm
from data_base.utils import silence_stdout
import time
import sys
import math
import glob

class RW:
    def __init__(self, df_seeds = None, param_ranges = None, 
                 params_to_explore = None, evaluation_function = None, 
                 MAIN_DIRECTORY = None, min_step_size = 0, max_step_size = 0.02, 
                 checkpoint_every = 100, n_iterations = 60000,
                 mode = None, aim_params={}, stop_n_inside_with_aim_params = -1):
        '''Class to perform RW exploration from a seedpoint.
        
        df_seeds: pandas dataframe which contains the individual seed points as rows and 
            the parameters as columns
            
        param_ranges: pandas dataframe, which contains the parameters as rows and has a 
            "min_" and "max_" column denoting range of values this parameter may take
            
        params_to_explore: list of parameters that should be explored. If None, all parameters are explored.
            
        evaluation_function: takes one argument (a new parameter vector), returns 
            inside, evaluation. 
                inside: boolean that indicates if the parameter vector is within experimental constraits
                    (i.e. results in acceptable physiology) or not. 
                evaluation: dictionary that will be saved alongside the parameters. For example, this should contain
                    ephys features.
        
        mode: None: default random walk. 
              'expand': only propose new points that move further away from seedpoint
                    
        aim_params: this param will make the exploration algorithm propose only new points such that a set of 
            parameters aims certain values during exploration.
            Empty dictionary by default. Dictionary with the parameters as keys and their aim values as values.
        
        stop_n_inside_with_aim_params: number of successful models / set of parameters inside space with aim_params 
            to find before stopping exploration
                    
        MAIN_DIRECTORY: output directory in which results are stored.'''
        self.df_seeds = df_seeds
        self.param_ranges = param_ranges
        self.MAIN_DIRECTORY = MAIN_DIRECTORY
        self.evaluation_function = evaluation_function
        self.min_step_size = min_step_size
        self.max_step_size = max_step_size
        self.checkpoint_every = checkpoint_every
        self.all_param_names = list(self.param_ranges.index)
        self.n_iterations = n_iterations
        self.mode = mode
        if params_to_explore is None:
            self.params_to_explore = self.all_param_names
        else:
            self.params_to_explore = params_to_explore
        self.aim_params = aim_params
        self.normalized_aim_params = self._normalize_aim_params(aim_params)
        self.stop_n_inside_with_aim_params = stop_n_inside_with_aim_params
    
    def _normalize_aim_params(self,aim_params):
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
        
    def assess_aim_params_reached(self, normalized_params):
        reached_aim_params = []
        for key in self.aim_params.keys():
            idx = self.params_to_explore.index(key)
            reached_aim_params.append(math.isclose(normalized_params[idx],self.normalized_aim_params[key],abs_tol=self.max_step_size))
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
        print(len(seed_point_for_exploration_pd)) # this is the point in space to start exploring
        # normalize seed point parameters
        seed_point_for_exploration_normalized_pd = self._normalize_params(seed_point_for_exploration_pd)
        seed_point_for_exploration_normalized_selected_np = seed_point_for_exploration_normalized_pd[self.params_to_explore].values
        
        # set seed
        assert(seed is not None)
        np.random.seed(seed)    
        
        # set up folder structure
        print('My random number generator seed is', seed)
        OPERATION_DIR = os.path.join(self.MAIN_DIRECTORY, '{}/{}'.format(selected_seedpoint, particle_id))
        if not os.path.exists(OPERATION_DIR):
            os.makedirs(OPERATION_DIR)
        print('I am particle', particle_id, 'and I write to', OPERATION_DIR)
        
        # check if we start from scratch or if we resume an exploration
        iterations = [int(f.split('.')[0]) for f in os.listdir(OPERATION_DIR) if f.endswith('.pickle')]
        iterations = sorted(iterations,reverse=True)
        if iterations and max(iterations) > 60000:
            print('more than 60000 iterations done. exit gracegfully')
            return 
            #sys.exit(0)
        if len(iterations) == 0:
            print('So far nothing simulated, start from seedpoint', selected_seedpoint)
            p = seed_point_for_exploration_pd # p is pandas and the full vector and unnormalized
            iteration = 0
            inside, initial_evaluation = self.evaluation_function(p) # inside determines if the evaluation has been successful or not
            assert(inside)
            initial_evaluation['inside'] = inside
            out = [initial_evaluation]  # out is what will be saved
        else:
            # search for last model inside the space, starting from the previous saved iteration
            for iteration in iterations:
                df_path = os.path.join(OPERATION_DIR, '{}.pickle'.format(iteration))
                print('Found preexisting RW, continue from there. Iteration', iteration)
                print('Loading file', df_path) 
                df = pd.read_pickle(df_path)   
                df = df[df.inside]
                try:
                    p = df.iloc[-1][self.all_param_names] # p is pandas and the full vector and unnormalized
                    break
                except IndexError:
                    print("didn't find a model inside the space, try previous iteration")
            
            out = []
            # set the random number generator to the latest state
            assert(max(iterations) == iterations[0])
            rngn_path = os.path.join(OPERATION_DIR, '{}.pickle.rngn'.format(iterations[0]))
            with open(rngn_path, 'rb') as f:
                rngn = cloudpickle.load(f)
            print('set state of random number generator')
            np.random.set_state(rngn)
            
            # set current iteration to follow up on the latest saved iteration
            iteration = iterations[0] + 1
            out = [] # out is what is saved 
        
        p_normalized = self._normalize_params(p)
        p_normalized_selected_np = p_normalized[self.params_to_explore].values
        reached_aim_params = self.assess_aim_params_reached(p_normalized)
        
        # exploration loop
        print('exploration loop')
        while True:
            print('New loop. Current iteration', iteration)
            if iteration % self.checkpoint_every == 0 and iteration > 0:
                print('--- Saving')
                df_path = os.path.join(OPERATION_DIR, '{}.pickle'.format(iteration))
                df = pd.DataFrame(out)
                df.to_pickle(df_path + '.saving')
                with open(df_path + '.rngn', 'wb') as f:
                    cloudpickle.dump(np.random.get_state(), f)  
                # deal with the case that exploration was interupted while saving the dataframe
                shutil.move(df_path + '.saving', df_path) 
                out = [] # reset output after saving
                
            # this inner loop suggests new movements until the suggested step is within bounds
            print('Get new position')    
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
                            print('new position increases distance by {}'.format(delta_dist))
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
                    
            print('Position within boundaries found, step size is', step_size, 
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
            print('Inside the space?', inside)
            evaluation['n_suggestion'] = n_suggestion
            evaluation['inside'] = inside
            out.append(evaluation)
            if inside:
                for key in self.normalized_aim_params.keys():
                    idx = self.params_to_explore.index(key)
                    print(key,' (normalized) - current: ', np.round(p_normalized_selected_np[idx],4),', proposed: ', np.round(p_normalized[key],4))
                print('Moving current position to proposed position')
                p_normalized_selected_np = p_proposal
                print('distance to initial seed point (normalized):', get_vector_norm(p_normalized_selected_np-seed_point_for_exploration_normalized_selected_np))
                reached_aim_params = self.assess_aim_params_reached(p_normalized)
                if all(reached_aim_params) and len(reached_aim_params)!=0:
                    print('Reached all aim parameters! Creating flag in seedpoint directory...')
                    seedpoint_dir = os.path.join(self.MAIN_DIRECTORY, '{}'.format(selected_seedpoint))
                    aim_params_inside_flag = glob.glob(os.path.join(seedpoint_dir,'aim_params_successful_model_*'))
                    if len(aim_params_inside_flag) == 0:
                        open(os.path.join(seedpoint_dir,'aim_params_successful_model_1'), 'a').close()
                        count = 1
                    else:
                        count = int(aim_params_inside_flag[0].split('_')[-1])
                        count+=1
                        os.rename(aim_params_inside_flag[0], os.path.join(path,'aim_params_successful_model_{}'.format(count)))
                    if count == self.stop_n_inside_with_aim_params:
                        print('Reached aim params {} times for successful models. Exit gracefully'.format(count))
                        break
            iteration += 1