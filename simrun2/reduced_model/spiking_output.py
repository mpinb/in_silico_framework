from functools import partial
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def convolve_matrix_with_kernel(X, kernel):
    l_kern = len(kernel)
    l_xrow = X.shape[0]
    l_xcol = X.shape[1]
    #X = np.c_[np.zeros((l_xrow,l_kern - 1)), X]
    #np.testing.assert_array_equal(X.shape, [l_xrow, l_xcol + l_kern - 1])
    X = np.c_[np.zeros((l_xrow, l_kern)), X]
    np.testing.assert_array_equal(X.shape, [l_xrow, l_xcol + l_kern])
    ret = np.array([np.dot(X[:, t:t + l_kern], kernel) for t in range(l_xcol)])
    return np.transpose(ret)


#def rolling_window(a, window):
#    '''http://www.rigtorp.se/2011/01/01/rolling-statistics-numpy.html'''
#    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
#    strides = a.strides + (a.strides[-1],)
#    return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)
#
#def convolve_matrix_with_kernel(X, kernel):
#    l_kern = len(kernel)
#    l_xrow = X.shape[0]
#    l_xcol = X.shape[1]
#    X = np.c_[np.zeros((l_xrow,l_kern)), X]
#    np.testing.assert_array_equal(X.shape, [l_xrow, l_xcol + l_kern])
#    X = rolling_window(X, len(kernel))
#    return np.dot(X, kernel)

# def synaptic_input_to_lda_values(X, t, start = 0, n = 1000):
#     #calculate lda values of selected trails (start, n) at selected timepoint (t)
#     EXC = np.c_[np.zeros((n,l)), X[:,:300]]
#     INH = np.c_[np.zeros((n,l)), X[:,300:]]
#     EXC = EXC[:,180+t+l:265+t+l]
#     INH = INH[:,180+t+l:265+t+l]
#     #calculate PSTH from lda_values
#     lda_values = np.dot(np.concatenate([EXC, INH], axis = 1), coef_)
#     return lda_values


def data2Convolutions(X_dict, kernel_dict):
    return {
        name: convolve_matrix_with_kernel(X_dict[name], kernel_dict[name])
        for name in list(kernel_dict.keys())
    }


def convolutions2weightedNetInputs(convolutions_dict, combine_fun=sum):
    return combine_fun(
        [convolutions_dict[name] for name in list(convolutions_dict.keys())])


def weightedNetInput2spikingProbabilities(weighted_net_input,
                                          nonlinearity,
                                          LUT_resolution=1):
    weighted_net_input = np.round(
        weighted_net_input / LUT_resolution) * LUT_resolution
    weighted_net_input[weighted_net_input < nonlinearity.index.min(
    )] = nonlinearity[nonlinearity.index.min()]
    weighted_net_input[weighted_net_input > nonlinearity.index.max(
    )] = nonlinearity[nonlinearity.index.max()]
    out = np.array([
        nonlinearity[weighted_net_input[:, n]].values
        for n in range(weighted_net_input.shape[1])
    ])
    return np.transpose(out)


def spikingProbabilities2rawPSTH(spiking_probabilities):
    return np.mean(spiking_probabilities, axis=0)


def calculateFractionAbleToSpike(rawPSTH, refractory_period):
    able_to_spike = [1]
    n_deactivated = [0]
    for e in rawPSTH:
        diff = able_to_spike[
            -1] * e  # amount of trails that would spike right now
        if len(n_deactivated) >= refractory_period:
            activated = n_deactivated[-refractory_period]
        else:
            activated = 0
        n_deactivated.append(diff)
        able_to_spike.append(able_to_spike[-1] - diff + activated)
    return able_to_spike


def correct_PSTH_by_refractory_period(PSTH, refractory_period):
    '''return_ = 'only_PSTH' or  'PSTH_and_abletospike' '''
    if not refractory_period:
        return np.ones(len(PSTH))
    able_to_spike = [1]
    n_deactivated = [0]
    for e in PSTH:
        diff = able_to_spike[
            -1] * e  # amount of trails that would spike right now
        if len(n_deactivated) >= refractory_period:
            activated = n_deactivated[-refractory_period]
        else:
            activated = 0
        n_deactivated.append(diff)
        able_to_spike.append(able_to_spike[-1] - diff + activated)

    return able_to_spike


def calculatePSTH(rawPSTH, able_to_spike):
    return [a * b for a, b, in zip(rawPSTH, able_to_spike)]


def apply_reduced_model(X_dict,
                        kernel_dict=None,
                        nonlinearity_LUT=None,
                        refractory_period=None,
                        combine_fun=sum,
                        LUT_resolution=1):
    convolutions_dict = data2Convolutions(X_dict, kernel_dict)
    weighted_net_input = convolutions2weightedNetInputs(convolutions_dict,
                                                        combine_fun)
    nonlinearity = nonlinearity_LUT[refractory_period]
    spiking_probabilities = weightedNetInput2spikingProbabilities(
        weighted_net_input, nonlinearity, LUT_resolution)
    rawPSTH = spikingProbabilities2rawPSTH(spiking_probabilities)
    able_to_spike = correct_PSTH_by_refractory_period(rawPSTH,
                                                      refractory_period)
    PSTH = calculatePSTH(rawPSTH, able_to_spike)
    return {'convolutions_dict': convolutions_dict, 'weighted_net_input': weighted_net_input, \
           'spiking_probabilities': spiking_probabilities, 'rawPSTH': rawPSTH, \
           'able_to_spike': able_to_spike, 'PSTH': PSTH}


def get_reduced_model(kernel_dict,
                      nonlinearity_LUT,
                      refractory_period,
                      combine_fun=sum,
                      LUT_resolution=1):
    '''returns a function which you can feed with data and which will return evaluation results of the reduced model.
    
    kernel_dict: dictionary of kernels, e.g. if you have a seperated kernel for EXC and INH input, 
        you could use {'EXC': [0,0,1], 'INH': [0,1,1]}
    
    nonlinearity_LUT: dictionary, that contains values of nonlinearity. Keys are refractory periods. E.g.
        you could have a dict like this: {0: pd.Series([0,0,.1,.2,.4,.3,.1,0,0]), 10: pd.Series([[0,0,.1,.2,.4,.8,1,1,1]])}.
    
    combine_fun: function to combine convolutions of a single trail together. Default:  sum
    
    LUT_resolution: reolution of the nonlinearity_LUT. E.g. in case LUT_resolution == 1, the pd.Series objects 
        in the nonlinearity_LUT are expect to have keys for [...,0,1,2,3, ...], in case of LUT_resolution == 2,
        the pd.Series objects in the nonlinearity_LUT are expect to have keys for [...,0,2,4,6, ...]
    '''

    return partial(apply_reduced_model, kernel_dict = kernel_dict, nonlinearity_LUT = nonlinearity_LUT, \
                   refractory_period = refractory_period, combine_fun = combine_fun, LUT_resolution = LUT_resolution)


# tests
INH = np.array([[0, 1, 1, 0, 0, 0]])
EXC = np.array([[0, 1, 1, 0, 0, 0]])
kernel_dict = {'EXC': [0, 0, 1], 'INH': [0, 1, 1]}
nonlinearity_LUT = {0: pd.Series({-1: 0, 0: 0, 1: 1, 2: 1})}
rm = get_reduced_model(kernel_dict, nonlinearity_LUT, 0)
out = rm({'EXC': EXC, 'INH': INH})

np.testing.assert_equal(out['convolutions_dict']['EXC'], [[0, 0, 1, 1, 0, 0]])
np.testing.assert_equal(out['convolutions_dict']['INH'], [[0, 0, 1, 2, 1, 0]])
np.testing.assert_equal(out['weighted_net_input'], [[0, 0, 2, 3, 1, 0]])
np.testing.assert_equal(out['spiking_probabilities'], [[0, 0, 1, 1, 1, 0]])
np.testing.assert_equal(out['rawPSTH'], [0, 0, 1, 1, 1, 0])
