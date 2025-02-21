'''
This module concerns itself with setting up a cell with biophysical details and simulation parameters.

The :py:class:`~biophysics_fitting.simulator.Simulator_Setup` class is an inherent attribute of the :py:class:`~biophysics_fitting.simulator.Simulator` class, and should only be accessed as such.
It takes care of equipping a cell with biophysical details, using convenient pd.Series objects as parameter vectors.

The class :py:class:`~biophysics_fitting.simulator.Simulator` is used to transform a parameter vector into simulated voltage traces.
It allows to apply a variety of stimuli to the cell and extract voltage traces.

The results of this module can be used in conjunction with :py:mod:`~biophysics_fitting.evaluator` to iteratively run and evaluate simulations.
'''

import single_cell_parser as scp
from .parameters import param_selector
import time
import logging
logger = logging.getLogger("ISF").getChild(__name__)

__author__ = 'Arco Bast'
__date__ = '2018-11-08'


class Simulator_Setup:
    """Class for setting up cells with biophysical details.
    
    This class is an inherent attribute of the :py:class:`~biophysics_fitting.simulator.Simulator` class, and should only be accessed as such.
    This class concerns with setting up a cell with biophysical details.
    
    Usually, a simulation contains fixed parameters, specific to the cell (e.g. the filename of the morphology)
    and/or stimulus protocol (e.g. recording sites). Such fixed parameters can be defined by adding
    :py:meth:`~biophysics_fitting.parameters.set_fixed_params` to :paramref:`param_modify_funs`. 
    A typical usecase is to use the fixed parameters to specify to soma distance for a voltage trace 
    of the apical dendrite. Make sure that the :py:class:`~biophysics_fitting.simulator.Simulator` :paramref:`stim_run_fun` reads the 
    parameter :paramref:`recSite` and sets up the stimulus accordingly (see :py:class:`~biophysics_fitting.simulator.Simulator`).
    
    Example::

        >>> def param_modify_function(params):
        >>>    # alter params
        >>>    return params
           
        >>> def cell_params_generator(params, template):
        >>>    cell_params = template.copy()
        >>>    # Fill in template with params
        >>>    return cell_params
            
        >>> def cell_param_modify_function(cell_params):
        >>>     # alter cell_params
        >>>     return cell_params
            
        >>> def cell_generator(cell_params):
        >>>     return single_cell_parser.create_cell(cell_params)
            
        >>> def cell_modify_functions(cell):
        >>>     # alter cell
        >>>     return cell
            
        >>> s = Simulator() # instantiate simulator object
        >>> fixed_params = {'stim_1.measure_fun.recSite': 835, 'stim_1.stim_setup.dist': 835}
        >>> s.setup.params_modify_funs.append([
            'fixed_params', 
            partial(set_fixed_params, fixed_params=fixed_params)
            ])
        >>> s.setup.cell_param_generator =  cell_params_generator
        >>> s.setup.cell_generator = cell_generator
        >>> s.setup.params_modify_funs.append(['modify_param_1', param_modify_fun])
        >>> s.setup.cell_param_modify_funs.append(['modify_cell_param_1', cell_param_modify_fun])
        >>> s.setup.cell_modify_funs.append(['modify_cell_1', cell_modify_fun])
        
    Notable methods:
    
        >>> s.setup.get(params)
        cell, params
    
    Each function that receives the biophysical parameter vector 
    (i.e. :paramref:`cell_param_modify_funs` and :paramref:`cell_modify_funs`)
    only sees a subset of the parameter vector that is provided by the user. This subset is determined 
    by the name by which the function is registered.
    
    Example::

        >>> params = {
        >>>     'apical_scaling.scale': 2,
        >>>     'ephys.soma.gKv': 0.001,
        >>>     'ephys.soma.gNav': 0.01
        >>>    }

        >>> def scale_apical(params, **kwargs):
        >>>     params['scale'] = kwargs['scale']
        
        >>> def ephys(cell, **kwargs):
        >>>     cell.soma.gKv = kwargs['soma.gKv']
        >>>     cell.soma.gNav = kwargs['soma.Nav']
        
        >>> s.setup.params_modify_funs.append([
            'apical_scaling',  # name must equal the prefix of the parameter, i.e. 'apical_scaling'
            partial(scale_apical, 'scale' = 2)])
        >>> s.setup.cell_modify_funs.append([
            'ephys',  # name must equal the prefix of the parameter, i.e. 'ephys'
            partial(ephys, 'soma.gKv'=1, 'soma.gNav'=2)])
    
    Attributes:
        cell_param_generator (callable): A function that generates a :py:class:`~sumatra.parameters.NTParameterSet` cell parameter object.
        cell_param_modify_funs (list): list of functions that modify the cell parameters.
        cell_generator (callable): A function that generates a :py:class:`~single_cell_parser.cell.Cell` object.
        cell_modify_funs (list): List of functions that modify the cell object.
        stim_setup_funs (list): List of functions that set up the stimulus.
        stim_run_funs (list): List of functions that each run a simulation.
        stim_response_measure_funs (list): List of functions that extract voltage traces from the cell.
        params_modify_funs (list): List of functions that modify the biophysical parameter vector.
        check_funs (list): List of functions that check the setup. Useful for debugging.
    
    """
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
        """Check if the setup is correct.
        
        This method checks if the :py:class:`Simulator_Setup` object is set up correctly.
        
        It checks if:
        
        - :paramref:`cell_param_generator` is set.
        - :paramref:`cell_generator` is set.
        - The first element of the names of the :paramref:`stim_setup_funs`, :paramref:`stim_run_funs` and :paramref:`stim_response_measure_funs` are the same.
          These names are used to group the functions that belong to the same stimulus.
        - The number of :paramref:`stim_setup_funs`, :paramref:`stim_run_funs` and :paramref:`stim_response_measure_funs` are the same.
        - Calls each additional check function in :paramref:`check_funs`.
        """
        if self.cell_param_generator is None:
            raise ValueError('cell_param_generator must be set')
        if self.cell_generator is None:
            raise ValueError('cell_generator must be set')
        self._check_first_element_of_name_is_the_same(
            self.stim_setup_funs,
            self.stim_run_funs)
        self._check_first_element_of_name_is_the_same(
            self.stim_setup_funs, 
            self.stim_response_measure_funs)
        for fun in self.check_funs:
            fun()
        #if not len(self.stim_setup_funs) == len(self.stim_result_extraction_fun):
        #    raise ValueError('run_fun must be set')

    def _check_not_none(self, var, varname, procedure_description):
        """Convenience method to check if the output of some method is not None.
        
        Used as sanity check throughout this class.
        
        Args:
            var: The variable to check.
            varname (str): The name of the variable.
            procedure_description (str): A description of the procedure that produced the variable.
            
        Raises:
            ValueError: If :paramref:`var` is None.
        """
        if var is None:
            raise ValueError('{} is None after execution of {}. '.format(
                varname, procedure_description) +
                             'Please check, that the function returns a value!')

    def _check_first_element_of_name_is_the_same(self, list1, list2):
        """Check if the first element of the names of two lists are the same.
        
        Note that :paramref:`list1` and :paramref:`list2` are lists of lists, where the first element of each list is
        the name of the routine, and the second element is the function associated to the routine.
        The names are thus not the function names necessarily. In general, these routine names
        are dot-separated strings that start with the stimulus they refer to e.g. ``'stim_1.setup'``.
        
        Args:
            list1 (list): A list of function tags.
            list2 (list): A list of function tags.
            
        Raises:
            ValueError: If the first element of the names of the two lists are not the same.
        """
        # lists are stim_setup_funs, stim_run_funs, response_measure_fun

        # extract names
        names1 = [x[0] for x in list1]
        names2 = [x[0] for x in list2]

        # prefix
        prefix1 = list({x.split('.')[0] for x in names1})
        prefix2 = list({x.split('.')[0] for x in names2})

        assert tuple(sorted(prefix1)) == tuple(sorted(prefix2))

    def get_stims(self):
        """Get the names of the stimuli."""
        return [x[0].split('.')[0] for x in self.stim_run_funs]

    def get_stim_setup_fun_by_stim(self, stim):
        """Get the stimulus setup function by stimulus name.
        
        Stimulus setup functions are functions that set up the stimulus.
        They are saved under the name ``stimulus_name.setup``, and accessible
        under :paramref:`stim_setup_funs`.
        
        Args:
            stim (str): The stimulus name, e.g. ``'stim_1'``, ``'bAP'``, ``'StepOne'``.
            
        Returns:
            Callable: The setup function for the stimulus.
        """
        l = [x for x in self.stim_setup_funs if x[0].split('.')[0] == stim]
        assert len(l) == 1
        return l[0]

    def get_stim_run_fun_by_stim(self, stim):
        """Get the stimulus run function by stimulus name.
        
        Stimulus run functions are functions that run the simulation.
        They are saved under the name ``stimulus_name.run``, and accessible
        under :paramref:`stim_run_funs`.
        
        Args:
            stim (str): The stimulus name, e.g. ``'stim_1'``, ``'bAP'``, ``'StepOne'``.
            
        Returns:
            Callable: The run function for the stimulus.
        """
        l = [x for x in self.stim_run_funs if x[0].split('.')[0] == stim]
        assert len(l) > 0, "No stimulus run function is configured for simulus {}. Did you configure this stimulus, or was it overridden at some point?".format(stim) 
        assert len(l) == 1, "Multiple stimulus run functions are configured for stimulus {}. This is not allowed, as i can only run one stimulus at a time.".format(stim)
        return l[0]

    def get_stim_response_measure_fun(self, stim):
        """Get the stimulus response measure function by stimulus name.
        
        Stimulus response measure functions are functions that extract voltage traces from the cell.
        They are saved under the name ``stimulus_name.measure``, and accessible
        under :paramref:`stim_response_measure_funs`.
        
        Args:
            stim (str): The stimulus name, e.g. ``'stim_1'``, ``'bAP'``, ``'StepOne'``.       
        
        Returns:
            list: A list of functions that extract the voltage traces from the cell
        """
        l = [
            x for x in self.stim_response_measure_funs
            if x[0].split('.')[0] == stim
        ]
        return l  # [0]

    def get_params(self, params):
        '''Get the modified biophysical parameters.
        
        Applies each method in :paramref:`params_modify_funs` to the parameter vector.
        
        Args:
            params (pd.Series): The parameter vector.
            
        Returns:
            (pd.Series): Modified parameters.
        '''
        for name, fun in self.params_modify_funs:
            logger.info("Applying {} to params".format(name))
            params = fun(params)
        return params

    def get_params_after_cell_generation(self, params, cell):
        '''Get the cell parameters that have been modified by :paramref:`params_modify_funs_after_cell_generation`.
        
        Args:
            params (pd.Series): The parameter vector.
            cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
            
        Returns:
            pd.Series: The modified parameter vector.
            
        :skip-doc:
        
        TODO: does this modify the cell arameters or the biophysical parameter vector?
        '''
        for name, fun in self.params_modify_funs_after_cell_generation:
            params = fun(params,cell)
        return params

    def get_cell_params(self, params):
        '''Get the cell parameters as an NTParameterSet from the parameter vector.
        
        This can be used with :py:meth:`single_cell_parser.create_cell` to
        create a :py:class:`~single_cell_parser.cell.Cell` object.
        This is helpful for inspecting what parameters have effectively been used for the simulation.
        
        Args:
            params (pd.Series): The parameter vector.
            
        Returns:
            NTParameterSet: The cell parameters.
        '''
        params = self.get_params(params)
        cell_param = self.cell_param_generator()
        for name, fun in self.cell_param_modify_funs:
            #print name
            #print len(params), len(param_selector(params, name))
            try:
                cell_param = fun(cell_param, params=param_selector(params, name))
            except Exception as e:
                logger.error("Could not run the cell parameter modify function {} ({})".format(name, fun))
                logger.error(e)
                raise
            self._check_not_none(cell_param, 'cell_param', name)
        return cell_param

    def get_cell_params_with_default_sim_prams(
            self,
            params,
            recordingSites=[],
            tStart=0.0,
            tStop=295,
            dt=0.025,
            Vinit=-75.0,
            T=34.0):
        '''Get a neuron parameter object.
        
        Constructs a complete neuron parameter object that can be used for further simulations with e.g. :py:mod:`simrun`.
        
        Args:
            params (pd.Series): The parameter vector.
            recordingSites ([float]): The recording site (um).
            tStart (float): The start time of the simulation (ms).
            tStop (float): The stop time of the simulation (ms).
            dt (float): The time step of the simulation (ms).
            Vinit (float): The initial voltage (mV).
            T (float): The temperature (Celsius).
            
        Returns:
            NTParameterSet: The neuron parameter object.
        '''
        NTParameterSet = scp.NTParameterSet
        sim_param = {
            'tStart': tStart,
            'tStop': tStop,
            'dt': dt,
            'Vinit': Vinit,
            'T': T,
            'recordingSites': recordingSites
        }
        NMODL_mechanisms = {}
        return NTParameterSet({
            'neuron': self.get_cell_params(params),
            'sim': sim_param,
            'NMODL_mechanisms': NMODL_mechanisms
        })

    def get(self, params):
        '''Get the cell with set up biophysics and params. 
        
        This is the main interfac to set up a cell object with biophysical parameters.
        
        Args:
            params (pd.Series): Biophysical parameters
            
        Returns:
            cell, params: The cell object and the parameter vector.
        '''
        params = self.get_params(params) # we need to modify the params before we get the cell params
        cell_params = self.get_cell_params(params)
        #params = self.get_params(params)
        cell = self.cell_generator(cell_params)
        for name, fun in self.cell_modify_funs:
            #print len(param_selector(params, name))
            try:
                cell = fun(cell, params=param_selector(params, name))
            except Exception as e:
                logger.error("Could not run the cell modify function {} ({})\n{}".format(name, fun, e))
                raise
            self._check_not_none(cell, 'cell', name)
        return cell, params

class Simulator:
    '''This class can be used to transform a parameter vector into simulated voltage traces.
    
    This is typically done in two steps:
    
    1. Set up a cell with biophysics from a parameter vector. See :py:class:`~biophysics_fitting.simulator.Simulator_Setup`
    2. Apply a variety of stimuli to the cell and extract voltage traces.    
    
    An examplary specification of such a program flow can be found in the module :py:meth:`~biophysics_fitting.hay_complete_default_setup.get_Simulator`.
        
    The usual application is to specify biophysical parameters in a parameter vector and simulate
    current injection responses depending on these parameters.
    
    
    Example:
    
        >>> def stim_setup_fun(cell, params):
        >>>     # set up some stimulus
        >>>     return cell
        
        >>> def stim_run_fun(cell, params):
        >>>     # run the simulation
        >>>     return cell
 
        >>> def stim_response_measure_fun(cell, params)
        >>>     # extract voltage traces from the cell
        >>>     # Extract ionic currents from the cell?
        >>>     return result
    
        >>> params = pd.Series({"param1": 1, "param2": 2})
        
        >>> s = Simulator()
        >>> cell, params = s.setup.get(params)
        >>> s.setup.stim_setup_funs.append(
            ['stim_1.setup', stim_setup_fun])
        >>> s.setup.stim_run_funs.append(
            ['stim_1.run', stim_run_fun])
        >>> s.setup.stim_response_measure_funs.append(
            ['stim_1.measure', stim_response_measure_fun])
            
    Often, it is easier to write functions that accept keyword arguments instead of full parameter vectors
    This can be done by using :py:meth:`~biophysics_fitting.parameters.params_to_kwargs`.
    
    Example:
    
        >>> def stim_setup_function(cell, recSite = None):
        >>>    # I dont need the :paramref:`params` argument, but I ask recSite directly
        >>>    # set up current injection at soma distance recSite
        >>>    return cell
            
        >>> s.setup.stim_setup_funs.append([
                BAC.stim_setup, 
                params_to_kwargs(stim_setup_function)
            ])
    
    Notable methods::
    
        >>> s.run(params): returns a dictionary with the specified voltage traces for all stimuli
        {'stim_1': {'tVec': ..., 'vList': [[...], ...]}, 'stim_2': ...}
        
        >>> s.get_simulated_cell(params, stim)
        cell, params  # cell has simulation data
        
        >>> s.setup.get(params):
        cell  # with bipohysics set up
        
        >>> s.setup.get_cell_params(params)
        cell_params
        
        >>> s.setup.get_cell_params_with_default_sim_prams(params, ...)
        neuron_parameter_file
    
    Note:
        The names for stim_setup_funs, stim_run_funs and stim_response_measure_funs need to start
            with the name of the simulus followed by a dot. For each stimulus, each of the three
            functions needs to be defined exactly once. 
    
    Attributes:
        setup (:py:class:`~biophysics_fitting.simulator.Simulator_Setup`): A Simulator_Setup object that keeps track of the simulation setup.
    '''

    def __init__(self):
        self.setup = Simulator_Setup()

    def get_simulated_cell(self, params, stim, simulate = True): 
        '''Get the simulated cell.
        
        Args:
            params (pd.Series): The parameter vector of biophysical parameters.
            stim (str): The stimulus to apply.
            simulate (bool): Whether to run the simulation (True), or only set up the simulation (False).
            
        Returns:
            cell, params: The cell object and the parameter vector.
        
        '''
        t = time.time()
        # get cell object with biophysics
        cell, params = self.setup.get(params)
        # set up stimulus
        name, fun = self.setup.get_stim_setup_fun_by_stim(stim)
        #print name, param_selector(params, name)
        fun(cell, params=param_selector(params, name))
        # run simulation
        name, fun = self.setup.get_stim_run_fun_by_stim(stim)
        #print name,param_selector(params, name)
        if simulate:
            cell = fun(cell, params = param_selector(params, name))
            logger.info("simulating {} took {} seconds".format(stim, time.time()-t))
        return cell, params

    def run(self, params, stims=None):
        '''Simulates all stimuli for a given parameter vector.
        
        Args:
            params: The parameter vector.
            stims (str | [str]): which sitmuli to run. Either a str (for one stimulus) or a list of str.
            
        Returns: 
            dict: Dictionary where stim_response_measure_funs names are keys, 
            return values of the stim_response_measure_funs (usually voltage traces) are values.
            
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
                result = fun(cell, params=param_selector(params, name))
                out.update({name: result})
            del cell
        return out


def run_fun(
    cell,
    T=34.0,
    Vinit=-75.0,
    dt=0.025,
    recordingSites=[],
    tStart=0.0,
    tStop=250.0,
    vardt=True,
    silent=True):
    '''Default function to run a simulation.
    
    Args:
        cell: The cell object.
        T (float): The temperature (Celsius).
        Vinit (float): The initial voltage (mV).
        dt (float): The time step (ms).
        recordingSites ([float]): The recording sites (um).
        tStart (float): The start time of the simulation (ms).
        tStop (float): The stop time of the simulation (ms).
        vardt (bool): Whether to use variable time step.
        silent (bool): Whether to suppress output.
        
    Returns:
        :py:class:`~single_cell_parser.cell.Cell`: The cell object, containing simulation data.
    '''
    from sumatra.parameters import NTParameterSet
    sim = {
        'T': T,
        'Vinit': Vinit,
        'dt': dt,
        'recordingSites': recordingSites,
        'tStart': tStart,
        'tStop': tStop
    }
    scp.init_neuron_run(NTParameterSet(sim), vardt=vardt)
    return cell
