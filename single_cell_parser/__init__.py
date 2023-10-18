'''
cell parser and synapse mapper 
for single cell simulations
with NeuroNet subcellular synapse distributions
'''
import logging
log = logging.getLogger("ISF").getChild(__name__)
import tables #so florida servers have no problem with neuron
from .writer import write_cell_simulation
from .writer import write_landmark_file
from .writer import write_cell_synapse_locations
from .writer import write_synapse_activation_file
from .writer import write_synapse_weight_file
from .writer import write_sim_results
from .writer import write_all_traces
from .writer import write_PSTH
from .writer import write_presynaptic_spike_times
from .writer import write_spike_times_file
from .reader import read_scalar_field
from .reader import read_synapse_realization
from .reader import read_synapse_activation_file
from .reader import read_complete_synapse_activation_file
from .reader import read_spike_times_file
from .reader import read_synapse_weight_file
from .reader import read_landmark_file
from .synapse_mapper import SynapseMapper
from .cell import Cell, PySection, PointCell
from .cell import SynParameterChanger
from .cell_parser import CellParser
#from synapse import activate_functional_synapse
from .network import NetworkMapper
from .network_realizations import create_synapse_realization
from .network_realizations import create_functional_network
from . import network_param_modify_functions
#from sim_control import SimControl
import neuron
from sumatra.parameters import build_parameters as build_parameters_sumatra
from sumatra.parameters import NTParameterSet
import numpy as np
import warnings
from model_data_base.mdbopen import mdbopen

#------------------------------------------------------------------------------ 
# commonly used functions required for running single neuron simulations
#------------------------------------------------------------------------------ 
def build_parameters(filename, fast_but_security_risk = True):
    from model_data_base.mdbopen import resolve_mdb_path
    filename = resolve_mdb_path(filename)
        
    if fast_but_security_risk:
        # taking advantage of the fact that sumatra NTParameterSet produces 
        # valid python code
        with mdbopen(filename, 'r') as f:
            dummy = eval(f.read())
        return NTParameterSet(dummy)
    else:
        # slow, but does not call the evil 'eval' 
        return build_parameters_sumatra(filename)
        
    

def load_NMODL_parameters(parameters):
    '''
    automatically loads NMODL mechanisms from paths in parameter file
    '''
    for mech in list(parameters.NMODL_mechanisms.values()):
        neuron.load_mechanisms(mech)
    try:
        for mech in list(parameters.mech_globals.keys()):
                for param in parameters.mech_globals[mech]:
                    paramStr = param + '_' + mech + '='
                    paramStr += str(parameters.mech_globals[mech][param])
                    print('Setting global parameter', paramStr)
                    neuron.h(paramStr)
    except AttributeError:
        pass

def create_cell(parameters, scaleFunc=None, allPoints=False, setUpBiophysics = True,\
                silent = False):
    '''
    default way of creating NEURON cell models;
    includes spatial discretization and inserts
    biophysical mechanisms according to parameter file
    '''
    if scaleFunc is not None:
        warnings.warn('Keyword scaleFunc is deprecated! ' + 
                      'New: To ensure reproducability, scaleFunc should be specified in the parameters, as described in single_cell_parser.cell_modify_funs')
    log.info('-------------------------------')
    log.info('Starting setup of cell model...')
    axon = False
    
    if 'AIS' in list(parameters.keys()):
        axon = True
    
        
    log.info('Loading cell morphology...')
    parser = CellParser(parameters.filename)
    parser.spatialgraph_to_cell(parameters, axon, scaleFunc)
    if setUpBiophysics:
        log.info('Setting up biophysical model...')
        parser.set_up_biophysics(parameters, allPoints)
    log.info('-------------------------------')
    
    parser.apply_cell_modify_functions(parameters)       
    parser.cell.init_time_recording()
    parser.cell.parameters = parameters
    parser.cell.scaleFunc = scaleFunc
    parser.cell.allPoints = allPoints
    parser.cell.neuronParam = parameters
    return parser.cell

def init_neuron_run(simparam, vardt=False, *events):
    '''
    Default NEURON run with inital parameters
    according to parameter file.
    Optional parameters: callable "events" that are
    passed to Event objects holding a FInitializeHandler.
    This can be used to implement changes of parameters during
    the course of the simulation using h.cvode.event(t, "statement")
    in the supplied callable, where "statement" is another
    Python callable which may be used to change parameters.
    '''
#    use fixed time step for now
    neuron.h.load_file('stdrun.hoc')
    cvode = neuron.h.CVode()    
    if vardt:
        cvode.active(1)
        # minimum tolerance: heuristically
        # tested with BAC firing
        # to give good tradeoff accuracy/speed
#        cvode.atol(1e-2)
#        cvode.rtol(2e-3)
#    neuron.h('using_cvode_=1')
#    neuron.h('cvode_active(1)')
#    cvode.use_local_dt(1)
#    cvode.condition_order(2)
#    cvode.atol(1e-3)
#    cvode.rtol(1e-12)
    else:
        cvode.active(0)
    eventList = []
    for event in events:
        e = Event(event)
        eventList.append(e)
#        print 'added cvode event to EventList'
    neuron.h.dt = simparam.dt
    neuron.h.celsius = simparam.T
    vInitStr = 'v_init=' + str(simparam.Vinit)
    neuron.h(vInitStr)
    neuron.h('init()')
#    neuron.h('run()')
#    neuron.h.finitialize(simparam.Vinit)
    neuron.run(simparam.tStop)

def sec_distance_to_soma(currentSec):
    '''compute path length from sec(x=0) to soma'''
    parentSec = currentSec.parent
    dist = 0.0
    parentLabel = parentSec.label
    while parentLabel != 'Soma':
        dist += parentSec.L
        currentSec = parentSec
        parentSec = currentSec.parent
        parentLabel = parentSec.label
    return dist

class Event():
    def __init__(self, func):
        self.callback = func
        self.fih = neuron.h.FInitializeHandler(1, self.callback)
           
def spines_update_synapse_distribution_file(cell, synapse_distribution_file, new_synapse_distribution_file):
    '''Update the .syn file to correctly point to spine heads as excitatory synapse locations. Spines must already exist, so call after create_cell, using the same .syn file that was used to create the cell. new_synfile will be created if it does not already exist.'''
    ## update the .syn file
    spine_heads = []
    for sec in cell.sections:
        if sec.label == "SpineHead":
            spine_heads.append(sec)
            
    
    excitatory = ['L6cc', 'L2', 'VPM', 'L4py', 'L4ss', 'L4sp', 'L5st', 'L6ct', 'L34', 'L6ccinv', 'L5tt', 'Generic']

    with open(synapse_distribution_file, "r") as synapse_file:
        file_data = synapse_file.readlines()
    
    i = 0
    
    for n, line in enumerate(file_data):
        if n > 3: # line 5 is first line containing data
            line_split = line.split("\t")

            if (line_split[0].split("_"))[0] in excitatory:                

                file_data[n] = "\t".join((line_split[0], str(cell.sections.index(spine_heads[i])), str(1.0) + "\n"))
                i += 1


    with open(new_synapse_distribution_file, "w") as synapse_file:    
        synapse_file.writelines(file_data)
    log.info("Success: .syn file updated")
        
    
def spines_update_network_paramfile(new_synapse_distribution_file, network_paramfile, new_network_paramfile):
    '''update the network.param file to point to the new synapse distribution file'''
    network_param = build_parameters(network_paramfile)
    for i in list(network_param.network.keys()):
        network_param.network[i].synapses.distributionFile = new_synapse_distribution_file
    network_param.save(new_network_paramfile)
    log.info("Success: network.param file updated")
    


