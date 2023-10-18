'''
Created on Nov 08, 2018

@author: abast
'''

import os
from collections import defaultdict
import numpy as np
import pandas as pd
import neuron
h = neuron.h
import warnings
import sys
import contextlib, io
import logging
from .utils import StreamToLogger
log = logging.getLogger("ISF").getChild(__name__)
# moved to the bottom to resolve circular import
# from .hay_complete_default_setup import get_hay_problem_description, get_hay_objective_names, get_hay_params_pdf

neuron_basedir = os.path.join(os.path.dirname(__file__), 'MOEA_EH_minimal')

def setup_hay_evaluator(testing = False):
    '''
    this adds a stump cell to the neuron environment,which is
    necessary to acces the hay evaluate functions. For the vairalbe time step solver,
    this changes the step size and can therefore minimally change the results.
    before testing reproducability, it is therefore necessary to initialize
    the evaluator
    '''
    # todo: this also creates a cell which is simulated in neuron
    # therefore the evaluator should be set up without 
    # creating a cell
    #
    # also, this creates a lot of neuron variables
    import biophysics_fitting
    assert(os.path.exists(neuron_basedir))
    import neuron
    h = neuron.h
    
    
    log.warning(
        "Setting up hay evaluator. This loads several variables " + 
        "to the NEURON envioronment. Also, it creates a unconnected " + 
        "cell (which is very small ~ 1 compartment) which has the purpose " + 
        "to 'just be there' such that the functionality necessary to evaluate " + 
        "voltage traces is available. This has the side effect that in the " + 
        "case of the variable time step solver, the timesteps can be changed."
        )
    
    central_file_name = 'fit_config_89_CDK20050712_BAC_step_arco_run1.hoc'

    with StreamToLogger(log, 10) as sys.stdout:  # redirect to log with level DEBUG (10)
        try:
            neuron.h.central_file_name    
            if not neuron.h.central_file_name == central_file_name:
                raise ValueError('Once the central_file_name is set, it cannot be changed!')
        except AttributeError:
            #print 'setting up NEURON config'        
            h('chdir("{path}")'.format(path = neuron_basedir))
            h('strdef central_file_name')
            h('central_file_name = "{}"'.format(central_file_name))
            h('load_file("MOEA_gui_for_objective_calculation.hoc")')  
            if testing: 
                test()

def is_setup():
    import neuron
    h = neuron.h
    try:
        neuron.h.central_file_name 
        return True
    except AttributeError:
        return False
    
objectives_step = ['AI1','AI2','AI3','APh1','APh2','APh3','APw1','APw2','APw3','DI1','DI2',
'ISIcv1','ISIcv2','ISIcv3','TTFS1','TTFS2','TTFS3','fAHPd1','fAHPd2','fAHPd3',
'mf1','mf2','mf3','sAHPd1','sAHPd2','sAHPd3','sAHPt1','sAHPt2','sAHPt3']

objectives_BAC = ['BAC_APheight', 'BAC_ISI', 'BAC_ahpdepth', 'BAC_caSpike_height', 'BAC_caSpike_width', 
                      'BAC_spikecount', 'bAP_APheight', 'bAP_APwidth', 'bAP_att2', 'bAP_att3', 'bAP_spikecount']

##############################################
# used to test reproducibility
##############################################

def get_feasible_model_params():
    raise
    pdf = get_hay_params_pdf()
    x = [1.971849,   0.000363,   0.008663,   0.099860,   0.073318,   0.359781,   0.000530,   
         0.004958,   0.000545, 342.880108,   3.755353,   0.002518,   0.025765,   0.060558,   
         0.082471,   0.922328,   0.000096,   0.000032,   0.005209, 248.822554,   0.000025,   
         0.000047,   0.000074,   0.000039,   0.000436,   0.016033,   0.008445,   0.004921,   
         0.003024,   0.003099,   0.0005,   116.339356]  
    pdf['x'] = x
    return pdf

def get_feasible_model_objectives():
    raise
    pdf = get_hay_problem_description()
    index = get_hay_objective_names()
    y = [ 1.647,  3.037, 0.   ,  2.008,  2.228,  0.385,  1.745,  1.507,
         0.358,  1.454,  0.   ,  0.568,  0.893,  0.225,  0.75 ,  2.78 ,
         0.194,  1.427,  3.781,  5.829,  1.29 ,  0.268,  0.332,  1.281,
         0.831,  1.931,  0.243,  1.617,  1.765,  1.398,  1.126,  0.65 ,
         0.065,  0.142,  5.628,  6.852,  2.947,  1.771,  1.275,  2.079]  
    s = pd.Series(y, index = index)
    pdf.set_index('objective', drop = True, inplace = True)
    pdf['y'] = s
    return pdf

def hay_objective_function(x):
    '''evaluates L5tt cell Nr. 86 using the channel densities defined in x.
    x: numpy array of length 32 specifying the free parameters
    returns: np.array of length 5 representing the 5 objectives'''

    #import Interface as I
    setup_hay_evaluator()
    
    # put organism in list, because evaluator needs a list
    o = h.List()
    o.append(h.organism[0])
    # set genome with new channel densities
    x = h.Vector().from_python(x)

    h.organism[0].set_genome(x)
    with StreamToLogger(log, 10) as sys.stdout:  # redirect to log with level DEBUG (10)
        try:
            h.evaluator.evaluate_population(o)
        except:
            return [1000]*5
    return pd.Series(np.array(o[0].pass_fitness_vec()), index = get_hay_objective_names())

def test():
    '''compare the result of the optimization of the hay evaluator with a precomputed result'''
    print("Testing this only works, if you uncomment the following line in MOEA_gui_for_objective_calculation.hoc: ")
    print('// CreateNeuron(cell,"GAcell_v3") remove comment ")')
    print("However, this will slow down every NEURON evaluation (as an additional cell is created which will be")
    print("Included in all simulation runs. Therefore change this such that the cell is deleted afterwards or ")
    print("comment out the line again.")

    import numpy as np
    x = get_feasible_model_params().x
    y_new = hay_objective_function(x)
    y = get_feasible_model_objectives().y
    try:
        assert(max(np.abs((y - y_new[y.index].values))) < 0.05)
    except:
        print(y)
        print(y_new[y.index].values)
        raise


######################################
# actual evaluation
########################################


def get_cur_stim(stim): 
    setup_hay_evaluator() 
    sol = h.mc.get_sol() 
    stim_count = len(sol)
    return {sol.o(cur_stim).get_name().s: cur_stim for cur_stim in range(stim_count)}[stim]

def hay_evaluate(cur_stim, tvec, vList):
    '''note: I had the problem with python segfaulting as soon as this function got executed.
    In that case, make sure, the mechanisms are correctly compiled and loaded.
    You can load the mechanisms by importing the mechanisms module.'''
    setup_hay_evaluator()
    feature_mean_list = h.evaluator.feature_mean_list
    feature_std_list = h.evaluator.feature_std_list
    #tvec = h.evaluator.tvec
    #vList = h.evaluator.vList
    apc_vector = h.List() #h.evaluator.apc_vector
    stim1 = h.evaluator.stim1 ### need to figure out, what this is ... seems to be unused in the distance calculator itself
    penalty = 250 # h.evaluator.penalty
    use_density = 0# False # h.evaluator.use_density
    stimulus_feature_type_list = h.evaluator.stimulus_feature_type_list
    minspikenum = 2
    stim_vec = h.Vector(2)
    sol = h.mc.get_sol()       
    
    if sol.o(cur_stim).get_type().s == "SquarePulse":
        stim_vec.x[0]= sol.o(cur_stim).get_numerical_parameter("Delay") # 295
        stim_vec.x[1]= sol.o(cur_stim).get_numerical_parameter("Duration") # 5  
    elif sol.o(cur_stim).get_type().s == "bAP":
        stim_vec.x[0]= 295
        stim_vec.x[1]= 5          
        minspikenum = 1
    elif sol.o(cur_stim).get_type().s == "BAC":
        stim_vec.x[0]= 295
        stim_vec.x[1]= 45         
            
    hoc_tvec = h.Vector().from_python(tvec)
    hoc_vList = h.List()
    for v in vList:
        hoc_vList.append(h.Vector().from_python(v))

    with StreamToLogger(log, 10) as sys.stdout:  # redirect to log with level DEBUG (10)
        try:
            x = h.calculator.get_organism_stimulus_error(feature_mean_list.o(cur_stim),
                                            feature_std_list.o(cur_stim),
                                            hoc_tvec,
                                            hoc_vList,
                                            apc_vector, ## seems to be unused?
                                            stim1,
                                            penalty,
                                            use_density,
                                            cur_stim, # $o4 argument
                                            stimulus_feature_type_list.o(cur_stim),
                                            stim_vec,
                                            minspikenum)
        except RuntimeError: 
            # if incomplete simulation data is provided to the hay evaluate function,        
            # this raises an hoc error 
            return {k.s: 1000 for k in list(h.evaluator.stimulus_feature_name_list.o(cur_stim))}
    
    return {h.evaluator.stimulus_feature_name_list.o(cur_stim).o(lv).s: x for lv, x in enumerate(x)}
        

# # cleanly startup distance calculator

# h('dir = "."')
# dir_ = '.'
# central_file_name = 'fit_config_86_CDK20041214_BAC_run5.hoc'
# mc = h.MOEAConfig(central_file_name, dir_)
# TargetTracePath = 'L5PC_2'
# tdc = h.TrajectoryDensityCalculator()
# calculator = h.DistanceCalculator(mc,dir_,TargetTracePath,tdc)
# #h('calculator = new DistanceCalculator(mc,dir,TargetTracePath,tdc)')


# x = calculator.get_organism_stimulus_error(feature_mean_list.o(cur_stim),
#                                            feature_std_list.o(cur_stim),
#                                            tvec,
#                                            vList,
#                                            apc_vector, ## seems to be unused?
#                                            stim1,
#                                            penalty,
#                                            use_density,
#                                            cur_stim, # $o4 argument
#                                            stimulus_feature_type_list.o(cur_stim),
#                                            stim_vec,
#                                            minspikenum)

def hay_evaluate_bAP(tVec = None, vList = None):
    cur_stim = get_cur_stim('bAP')
    return hay_evaluate(cur_stim, tVec, vList)

def hay_evaluate_BAC(tVec = None, vList = None):
    cur_stim = get_cur_stim('BAC')
    return hay_evaluate(cur_stim, tVec, vList)

def hay_evaluate_StepOne(tVec = None, vList = None):
    cur_stim = get_cur_stim('StepOne')
    return hay_evaluate(cur_stim, tVec, vList)

def hay_evaluate_StepTwo(tVec = None, vList = None):
    cur_stim = get_cur_stim('StepTwo')
    return hay_evaluate(cur_stim, tVec, vList)

def hay_evaluate_StepThree(tVec = None, vList = None):
    cur_stim = get_cur_stim('StepThree')
    return hay_evaluate(cur_stim, tVec, vList)


from .hay_complete_default_setup import get_hay_problem_description, get_hay_objective_names, get_hay_params_pdf
