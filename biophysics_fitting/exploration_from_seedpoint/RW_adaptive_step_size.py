"""
This module provides code to perform a random walk with step size through biophysical parameter space.
This proved to not provide much additional speedup or accuracy for the usecase of the Oberlaender lab in Bonn (L5PT cells in the rat barrel cortex), and is not under development for the foreseeable future.

:skip-doc:
"""

# from functools import partial
# import os
# import pandas as pd
# import numpy as np
# import cloudpickle
# import shutil
# from .utils import get_vector_norm
# from data_base.utils import silence_stdout
# import time
# import sys
# 
# class RW_adaptive_step_size:
#     def __init__(self, df_seeds = None, param_ranges = None, 
#                  params_to_explore = None, evaluation_function = None, 
#                  MAIN_DIRECTORY = None, 
#                  initial_step_size = 0.01,
#                  checkpoint_every = 100):
#         '''Class to perform RW exploration from a seedpoint.
#         
#         df_seeds: pandas dataframe which contains the individual seed points as rows and 
#             the parameters as columns
#             
#         param_ranges: pandas dataframe, which contains the parameters as rows and has a 
#             "min_" and "max_" column denoting range of values this parameter may take
#             
#         params_to_explore: list of parameters that should be explored. If None, all parameters are explored.
#             
#         evaluation_function: takes one argument (a new parameter vector), returns 
#             inside, evaluation. 
#                 inside: boolean that indicates if the parameter vector is within experimental constraits
#                     (i.e. results in acceptable physiology) or not. 
#                 evaluation: dictionary that will be saved alongside the parameters. For example, this should contain
#                     ephys features.
#                     
#         MAIN_DIRECTORY: output directory in which results are stored.'''
#         self.df_seeds = df_seeds
#         self.param_ranges = param_ranges
#         self.MAIN_DIRECTORY = MAIN_DIRECTORY
#         self.evaluation_function = evaluation_function
#         self.initial_step_size = initial_step_size
#         self.checkpoint_every = checkpoint_every
#         self.all_param_names = list(self.param_ranges.index)
#         if params_to_explore is None:
#             self.params_to_explore = self.all_param_names
#         else:
#             self.params_to_explore = params_to_explore
#     
#     def _normalize_params(self,p):
#         assert(isinstance(p,pd.Series))
#         assert(len(p) == len(self.all_param_names))
#         min_ = self.param_ranges['min']
#         max_ = self.param_ranges['max']
#         return (p-min_)/(max_-min_)
#     
#     def _unnormalize_params(self, p):
#         assert(isinstance(p,pd.Series))
#         assert(len(p) == len(self.all_param_names))
#         min_ = self.param_ranges['min']
#         max_ = self.param_ranges['max']
#         return p*(max_-min_)+min_
#     
#     def _setup_signal_handler(self):
#         self.signal_received = False
#         self.exit = False
# 
#         return 
#         
#         import signal
#         self.exit = False
#         self.in_main_loop = False
#         def signal_handler(s, frame):
#             if self.in_main_loop == False:
#                 print('signal received, main loop has not started, exit without attempting to save')
#                 if s == signal.SIGUSR1:
#                     sys.exit(0)
#             else:
#                 print('signal received, main loop has started, setting flag to initiate saving')
#                 self.signal_received = True
#                 if s == signal.SIGUSR1:
#                     self.exit = True
#         signal.signal(signal.SIGUSR1, signal_handler)
#         signal.signal(signal.SIGTERM, signal_handler) 
#         signal.signal(signal.SIGINT, signal_handler)                
#         
#         
#     def run_RW(self, selected_seedpoint, particle_id, seed = None):
#         self._setup_signal_handler()
#         # get the parameters of the seed point (there might be more info in df_seeds than just the parameters)
#         seed_point_for_exploration_pd = self.df_seeds[self.params_to_explore].iloc[selected_seedpoint]
#         print(len(seed_point_for_exploration_pd))
#         # normalize seed point parameters
#         seed_point_for_exploration_normalized_pd = self._normalize_params(seed_point_for_exploration_pd)
#         seed_point_for_exploration_normalized_selected_np = seed_point_for_exploration_normalized_pd[self.params_to_explore].values
#         
#         # set seed
#         assert(seed is not None)
#         np.random.seed(seed)    
#         
#         # set up folder structure
#         print('My random number generator seed is', seed)
#         OPERATION_DIR = os.path.join(self.MAIN_DIRECTORY, '{}/{}'.format(selected_seedpoint, particle_id))
#         if not os.path.exists(OPERATION_DIR):
#             os.makedirs(OPERATION_DIR)
#         print('I am particle', particle_id, 'and I write to', OPERATION_DIR)
#         
#         def save():
#             import time
#             t0 = time.time()
#             print('Saving')
#             df_path = os.path.join(OPERATION_DIR, '{}.pickle'.format(iteration))
#             df = pd.DataFrame(out)
#             df.to_pickle(df_path + '.saving')
#             with open(df_path + '.rngn', 'wb') as f:
#                 cloudpickle.dump(np.random.get_state(), f)  
#             # deal with the case that exploration was interupted while saving the dataframe
#             shutil.move(df_path + '.saving', df_path)
#             print('saving took {} seconds'.format(time.time() - t0))
#             
#         # check if we start from scratch or if we resume an exploration
#         iterations = [int(f.split('.')[0]) for f in os.listdir(OPERATION_DIR) if f.endswith('.pickle')]
#         iterations = sorted(iterations,reverse=True)
#         if len(iterations) == 0:
#             print('So far nothing simulated, start from seedpoint', selected_seedpoint)
#             p = seed_point_for_exploration_pd # p is pandas and the full vector and unnormalized
#             iteration = 0
#             inside, initial_evaluation = self.evaluation_function(p)
#             assert(inside)
#             initial_evaluation['inside'] = inside
#             initial_evaluation['iteration'] = iteration
#             initial_evaluation['particle_id'] = particle_id
#             out = [initial_evaluation]  # out is what will be saved
#             step_size = self.initial_step_size
#         else:
#             # search for last model inside the space, starting from the previous saved iteration
#             for i, iteration in enumerate(iterations):
#                 df_path = os.path.join(OPERATION_DIR, '{}.pickle'.format(iteration))
#                 print('Found preexisting RW, continue from there. Iteration', iteration)
#                 print('Loading file', df_path) 
#                 df = pd.read_pickle(df_path)   
#                 if i == 0:
#                     step_size = df.iloc[-1]['step_size'] # set step size to the latest value
#                 df = df[df.inside]
#                 try:
#                     p = df.iloc[-1][self.all_param_names] # p is pandas and the full vector and unnormalized
#                     break
#                 except IndexError:
#                     print("didn't find a model inside the space, try previous iteration")
#             
#             out = []
#             # set the random number generator to the latest state
#             assert(max(iterations) == iterations[0])
#             rngn_path = os.path.join(OPERATION_DIR, '{}.pickle.rngn'.format(iterations[0]))
#             with open(rngn_path, 'rb') as f:
#                 rngn = cloudpickle.load(f)
#             print('set state of random number generator')
#             np.random.set_state(rngn)
#             
#             # set current iteration to follow up on the latest saved iteration
#             iteration = iterations[0] + 1
#             out = [] # out is what is saved 
#         
#         p_normalized = self._normalize_params(p)
#         p_normalized_selected_np = p_normalized[self.params_to_explore].values
#         
#         # exploration loop
#         print('exploration loop')
#         while True:
#             self.in_main_loop = True
#             print('New loop. Current iteration', iteration)
#             if iteration >= 60000:
#                 save()
#                 sys.exit(0)
#             if (iteration % 20 == 0 or self.signal_received) and iteration > 0:
#                 save() 
#                 if self.signal_received:
#                     print('saving after signal done')
#                     if self.exit:
#                         print('exiting gracefully')
#                         sys.exit(0)
#                     else:
#                         print('not exiting, waiting for SLURM kill')
#                         import time
#                         time.sleep(36000)
#                 out = [] # reset output after saving
#                 
#             # this inner loop suggests new movements until the suggested step is within bounds
#             print('Get new position')    
#             n_suggestion = 0        
#             while True:
#                 n_suggestion += 1
#                 movement = np.random.randn(len(self.params_to_explore))
#                 movement = movement/get_vector_norm(movement)
#                 movement = movement * step_size
#                 p_proposal = p_normalized_selected_np + movement    
#                 if p_proposal.max() <= 1 and p_proposal.min() >= 0:
#                     break
#             print('Position within boundaries found, step size is', step_size, 
#                   'Tested ', n_suggestion, 'positions to find one inside the box.') 
#             
#             # homogenize parameter representation
#             # note p_proposal is normalized and numpy
#             # p is pandas and the full vector and unnormalized
#             p = seed_point_for_exploration_normalized_pd.copy()
#             p[self.params_to_explore] = p_proposal
#             p = self._unnormalize_params(p)
#             
#             # evaluate new point
#             inside, evaluation = self.evaluation_function(p)
#             print('Inside the space?', inside)
#             evaluation['n_suggestion'] = n_suggestion
#             evaluation['inside'] = inside
#             evaluation['iteration'] = iteration
#             evaluation['particle_id'] = particle_id
#             evaluation['step_size'] = step_size
#             out.append(evaluation)
#             # update step size
#             if inside:
#                  step_size = step_size/0.97
#             else:
#                  step_size = step_size*0.97            
#             if inside:
#                 print('Moving current position to proposed position')
#                 p_normalized_selected_np = p_proposal
#                 print('distance to initial seed point (normalized):', 
#                       get_vector_norm(p_normalized_selected_np-seed_point_for_exploration_normalized_selected_np))
#             iteration += 1
# 