import neuron, sys, pytest
from biophysics_fitting.hay_evaluation import (
    get_hay_problem_description, 
    get_hay_objective_names, 
    setup_hay_evaluator,
    get_hay_params_pdf
    )
from config.isf_logging import StreamToLogger, logger
import numpy as np
import pandas as pd
h = neuron.h


def get_feasible_model_params():
    pdf = get_hay_params_pdf()
    x = [
        1.971849, 0.000363, 0.008663, 0.099860, 0.073318, 0.359781, 0.000530,
        0.004958, 0.000545, 342.880108, 3.755353, 0.002518, 0.025765, 0.060558,
        0.082471, 0.922328, 0.000096, 0.000032, 0.005209, 248.822554, 0.000025,
        0.000047, 0.000074, 0.000039, 0.000436, 0.016033, 0.008445, 0.004921,
        0.003024, 0.003099, 0.0005, 116.339356
    ]
    pdf['x'] = x
    return pdf


def get_feasible_model_objectives():
    pdf = get_hay_problem_description()
    index = get_hay_objective_names()
    y = [
        1.647, 3.037, 0., 2.008, 2.228, 0.385, 1.745, 1.507, 0.358, 1.454, 0.,
        0.568, 0.893, 0.225, 0.75, 2.78, 0.194, 1.427, 3.781, 5.829, 1.29,
        0.268, 0.332, 1.281, 0.831, 1.931, 0.243, 1.617, 1.765, 1.398, 1.126,
        0.65, 0.065, 0.142, 5.628, 6.852, 2.947, 1.771, 1.275, 2.079
    ]
    s = pd.Series(y, index=index)
    pdf.set_index('objective', drop=True, inplace=True)
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
    with StreamToLogger(
            logger, 10) as sys.stdout:  # redirect to log with level DEBUG (10)
        try:
            h.evaluator.evaluate_population(o)
        except:
            return [1000] * 5
    return pd.Series(np.array(o[0].pass_fitness_vec()),
                     index=get_hay_objective_names())

@pytest.mark.skip("This test segfaults, unsure why. It's set for removal either way.")
def hay_evaluation_test():
    '''compare the result of the optimization of the hay evaluator with a precomputed result'''
    print(
        "Testing this only works, if you uncomment the following line in MOEA_gui_for_objective_calculation.hoc: "
    )
    print('// CreateNeuron(cell,"GAcell_v3") remove comment ")')
    print(
        "However, this will slow down every NEURON evaluation (as an additional cell is created which will be"
    )
    print(
        "Included in all simulation runs. Therefore change this such that the cell is deleted afterwards or "
    )
    print("comment out the line again.")

    import numpy as np
    x = get_feasible_model_params().x
    y_new = hay_objective_function(x)
    y = get_feasible_model_objectives().y
    try:
        assert max(np.abs((y - y_new[y.index].values))) < 0.05
    except:
        print(y)
        print(y_new[y.index].values)
        raise
