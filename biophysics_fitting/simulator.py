'''
Created on Nov 08, 2018

@author: abast

For detailed documentation start with the docstring of the Simulator class.
'''

import single_cell_parser as scp
from .parameters import param_selector
import time
import logging
log = logging.getLogger("ISF").getChild(__name__)


class Simulator_Setup:
    def __init__(self):
        self.cell_param_generator = None
        self.cell_param_modify_funs = []
        self.cell_generator = None
        self.cell_modify_funs = []
        self.stim_setup_funs = []
        self.stim_run_funs = []
        self.stim_response_measure_funs = [] 
        self.params_modify_funs = []       
        self.check_funs = []
    
    def check(self):
        if self.cell_param_generator is None:
            raise ValueError('cell_param_generator must be set')
        if self.cell_generator is None:
            raise ValueError('cell_generator must be set')  
        self._check_first_element_of_name_is_the_same(self.stim_setup_funs, self.stim_run_funs)
        self._check_first_element_of_name_is_the_same(self.stim_setup_funs, self.stim_response_measure_funs)
        for fun in self.check_funs:
            fun()
        #if not len(self.stim_setup_funs) == len(self.stim_result_extraction_fun):
        #    raise ValueError('run_fun must be set') 
        
    def _check_not_none(self, var, varname, procedure_descirption):
        if var is None:
            raise ValueError('{} is None after execution of {}. '.format(varname, procedure_descirption) + 
                             'Please check, that the function returns a value!')
            
    def _check_first_element_of_name_is_the_same(self, list1, list2):
        # lists are stim_setup_funs, stim_run_funs, response_measure_fun
        
        # extract names
        names1 = [x[0] for x in list1]
        names2 = [x[0] for x in list2]
                 
        # prefix
        prefix1 = list({x.split('.')[0] for x in names1})
        prefix2 = list({x.split('.')[0] for x in names2})
        
        assert(tuple(sorted(prefix1)) == tuple(sorted(prefix2)))
        
    def get_stims(self):
        return [x[0].split('.')[0] for x in self.stim_run_funs]
    
    def get_stim_setup_fun_by_stim(self, stim):
        l = [x for x in self.stim_setup_funs if x[0].split('.')[0] == stim]
        assert(len(l) == 1)
        return l[0]
    
    def get_stim_run_fun_by_stim(self, stim):
        l = [x for x in self.stim_run_funs if x[0].split('.')[0] == stim]
        assert(len(l) == 1)
        return l[0]   
    
    def get_stim_response_measure_fun(self, stim):
        l = [x for x in self.stim_response_measure_funs if x[0].split('.')[0] == stim]
        return l # [0]     
    
    def get_params(self, params):
        '''returns cell parameters that have been modified by the params_modify_funs.'''
        for name, fun in self.params_modify_funs:
            params = fun(params)
        return params

    def get_cell_params(self, params):
        '''returns cell NTParameterSet structure used for the single_cell_parser.create_cell. 
        This is helpful for inspecting, what parameters have effectively been used for the simulation.
        
        Details, how to set up the Simulator are in the docstring of
        the Simulator class.'''
        params = self.get_params(params)
        cell_param = self.cell_param_generator()
        for name, fun in self.cell_param_modify_funs:
            #print name
            #print len(params), len(param_selector(params, name))            
            cell_param = fun(cell_param, params = param_selector(params, name))
            self._check_not_none(cell_param, 'cell_param', name)
        return cell_param    
    
    def get_cell_params_with_default_sim_prams(self, params, 
                                               recordingSites = [], 
                                               tStart = 0.0, 
                                               tStop = 295, 
                                               dt = 0.025,
                                               Vinit = -75.0,
                                               T = 34.0):
        '''returns complete neuron parameter object that can be used for further simulations
        i.e. with the simrun module or with roberts scripts.
        
        Details, how to set up the Simulator are in the docstring of
        the Simulator class.
        '''
        NTParameterSet = scp.NTParameterSet
        sim_param = {'tStart': tStart, 'tStop': tStop, 'dt': dt, 'Vinit': Vinit,
                     'T': T, 'recordingSites': recordingSites}
        NMODL_mechanisms = {}
        return NTParameterSet({'neuron': self.get_cell_params(params), 
                               'sim': sim_param, 
                               'NMODL_mechanisms': NMODL_mechanisms})
        
    def get(self, params):
        '''Returns a cell with set up biophysics and params. This is the main interface.
        
        Details, how to set up the Simulator are in the docstring of
        the Simulator class.'''
        # params = self.get_params(params) we do not want to apply this twice
        cell_params = self.get_cell_params(params)
        params = self.get_params(params)
        cell = self.cell_generator(cell_params)
        for name, fun in self.cell_modify_funs:
            #print len(param_selector(params, name))
            cell = fun(cell, params = param_selector(params, name))
            self._check_not_none(cell, 'cell', name)
        return cell, params


class Simulator:
    ''' This class can be used to transform a parameter vector into simulated voltage traces.

The usual application is to specify biophysical parameters in a parameter vector and simulate
current injection responses depending on these parameters.

For a simulator object s, the main functions are:
s.run(params): returns a dictionary with the specified voltagetraces for all stimuli
s.get_simulated_cell(params, stim): returns params and cell object for stimulus stim
s.setup.get(params):
    Returns a cell with set up biophysics
s.setup.get_cell_params(params): returns cell NTParameterSet structure used for the 
    single_cell_parser.create_cell. This is helpful for inspecting, what parameters 
    have effectively been used for the simulation
s.setup.get_cell_params_with_default_sim_prams(params, ...): returns complete neuron parameter file
    that can be used for further simulations, i.e. with the simrun module or with roberts scripts.

The "program flow" can be split in two parts.
(1) creating a cell object with set up biophysics from a parameter vector
(2) applying a variety of stimuli to such cell objects

An examplary specification of such a program flow can be found in the module hay_complete_default_setup.

The pipeline for (1) is as follows:
params: provided by the user: I.pd.Series object (keys: parameter names, values: parameter values)
    --> apply param_modify_functions (takes and returns a parameter vector, can alter it in any way)
          |
          |     |---- cell_param template
       cell_params_generator
          |     |
          v     v
cell_params: nested parameter structure, created from modified parameters and a template
    --> apply cell_param_modify_functions (takes and returns a NTParameterSet object, can alter it in any way)
          |
        cell_generator(cell_params)  
          |
          v
cell object: created from the modified cell_params object by calling the 'cell_generator'
    --> apply cell_modify_functions (takes and returns a cell object, can alter it in any way)
            Caveat: Try to avoid the usage of cell_modify_functions. While this allows 
            for any possible modification, it can be difficult to reproduce the result 
            later, as the cell object is different from what is expected by the cell_param 
            object. If possible, try to fully specify the cell in the cell_param object. Here,
            it is also possible to spcify cell modifying functions, see 
            single_cell_parser.cell_modify_functions.

What form do the functions need to have?
def example_cell_param_template_generator():
    #return a I.scp.NTParameterSet object as template. Ideally, all parameters, that need to be
    #filled in from the pasrameter vector have the value None, because it is tested, that
    #all None values have been replaced. E.g.
    return I.scp.NTParameterSet({'filename': path_to_hoc_morphology, 'Soma': somatic biophysical parameters})
    
def cell_generator(cell_param):
    return I.scp.create_cell(cell_params)
    
def example_cell_param_modify_function(cell_param, params)
    # do something to the cell param object depending on params
    return cell_param
    
def example_cell_modify_function(cell, params)
    # do something to the cell object depending on params
    return cell
        
Such functions can be registered to the Simlator object. Each function is registered with a name.

Each function, that receive the parameter vector (i.e. cell_param_modify_funs and cell_modify_funs)
only see a subset of the parameter vector that is provided by the user. This subset is determined 
by the name of the function.

E.g. let's assume, we have the parameters:
{'apical_scaling.scale': 2,
 'ephys.soma.gKv': 0.001,
 'ephys.soma.gNav': 0.01
 }

Then, a function that is registered under the name 'apical_scaling' would get the following parameters:
{'scale': 2}

The function, that is registered under the name 'ephys' would get the following parameters:
{'soma.gKv': 0.001,
 'soma.Nav': 0.01}
 
Usually, a simulation contains fixed parameters, e.g. the filename of the morphology. Such fixed
parameters can be defined 

How can pipeline (1) be set up?
s = Simulator() # instantiate simulator object
s.setup # Simualtor_Setup object, that contains all elements defining the pipeline above
s.setup.cell_param_generator =  example_cell_param_template_generator
s.setup.cell_generator = cell_generator
s.setup.params_modify_funs.append('name_of_param_modify_fun', example_cell_param_modify_function)
s.setup.cell_param_modify_funs.append('name_of_cell_param_modify_fun', example_cell_param_modify_function)
s.setup.cell_modify_funs.append('name_of_cell_modify_fun', example_cell_modify_function)

The pipeline for (2) is as follows:
Let s be the Simulator object

params: provided by the user: I.pd.Series object
   |
   |
  s.setup.get(params): triggers pipeline (1), results in a biophysically set up cell
   |
   v
For each stimulus: 
    --> stim_setup_funs
    --> stim_run_funs
    --> stim_response_measure_funs
       
What form do the functions need to have?
def stim_setup_funs(cell, params):
    # set up some stimulus
    return cell
    
def stim_run_fun(cell, params):
    # run the simulation
    return cell
    
def stim_response_measure_funs(cell, params)
    # extract voltage traces from the cell
    return result
    
How can pipeline (2) be set up?
The names for stim_setup_funs, stim_run_funs and stim_response_measure_funs need to start
with the name of the simulus followed by a dot. For each stimulus, each of the three
functions needs to be defined exatly once, e.g. you could do something like:

s.setup.stim_setup_funs.append(BAC.stim_setup, examplary_stim_setup_function)
s.setup.stim_run_funs.append(BAC.run_fun, examplary_stim_run_function)
s.setup.stim_response_measure_funs.append(BAC.measure_fun, examplary_stim_response_measure_function)

A typical usecase is to use the fixed parameters to specify to soma distance for a 
voltage trace of the apical dendrite. E.g.
{'BAC.measure_fun.recSite': 835,
'BAC.stim_setup.dist': 835}

You would need to make sure, that your examplary_stim_run_fun reads the parameter 'recSite'
and sets up the stimulus accordingly.

Often, it is easier to write functions, that do not accept a parameter vector, but instead
keyword arguments. E.g. it might be desirable to write the examplary_stim_setup_funs like this
def examplary_stim_setup_function(cell, recSite = None):
    # set up current injection at soma distance recSite
    return cell
    
Instead of:
def examplary_stim_setup_function(cell, params)
    recSite = params['recSite']
    # set up current injection at soma distance recSite
    return cell
    
This can be done by using the params_wo_kwargs method in biophysics_fitting.parameters. You would register
the function as follows:
s.setup.stim_setup_funs.append(BAC.stim_setup, params_to_kwargs(examplary_stim_setup_function))
'''
    def __init__(self):
        self.setup = Simulator_Setup()

    def get_simulated_cell(self, params, stim): 
        '''returns cell and parameters used to set up cell.
        The cell is simulated with the specified stimulus.
        
        Details, how to set up the Simulator are in the docstring of
        the Simulator class.'''
        t = time.time()
        # get cell object with biophysics            
        cell, params = self.setup.get(params) 
        # set up stimulus
        name, fun = self.setup.get_stim_setup_fun_by_stim(stim)
        #print name, param_selector(params, name)
        fun(cell, params = param_selector(params, name))
        # run simulation
        name, fun = self.setup.get_stim_run_fun_by_stim(stim)
        #print name,param_selector(params, name)
        cell = fun(cell, params = param_selector(params, name))
        log.info("simulating {} took {} seconds".format(stim, time.time()-t))
        return cell, params

    def run(self, params, stims = None):
            '''Simulates all stimuli for a given parameter vector.
            Returns: Dictionary where stim_response_measure_funs names are keys, 
            return values of the stim_response_measure_funs (usually voltage traces) are values.
            
            stims: which sitmuli to run. Either a str (for one stimulus) or a list of str.

            Details, how to set up the Simulator are in the docstring of
            the Simulator class.        
            '''
            if stims is None:
                stims = self.setup.get_stims()
            if isinstance(stims, str):
                stims = [stims]
            self.setup.check()
            out = {}            
            for stim in stims:
                cell, params = self.get_simulated_cell(params, stim)
                # extract result
                for name, fun in self.setup.get_stim_response_measure_fun(stim):
                    result = fun(cell, params = param_selector(params, name))
                    out.update({name: result})
                del cell
            return out

def run_fun(cell,
            T = 34.0, Vinit = -75.0, dt = 0.025, 
            recordingSites = [], tStart = 0.0, tStop = 250.0, 
            vardt = True, silent = True):
    '''Default function to run a simulation'''
    from sumatra.parameters import NTParameterSet
    sim = {'T': T,
           'Vinit': Vinit,
           'dt': dt,
           'recordingSites': recordingSites,
           'tStart': tStart,
           'tStop': tStop}    
    scp.init_neuron_run(NTParameterSet(sim), vardt = vardt)
    return cell