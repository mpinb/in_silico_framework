from biophysics_fitting.hay_evaluation import get_feasible_model_params, hay_objective_function, get_feasible_model_objectives
import numpy as np

# TODO: how to properly perform this test?
# def test():
#     '''compare the result of the optimization of the hay evaluator with a precomputed result'''
#     print("Testing this only works, if you uncomment the following line in MOEA_gui_for_objective_calculation.hoc: ")
#     print('// CreateNeuron(cell,"GAcell_v3") remove comment ")')
#     print("However, this will slow down every NEURON evaluation (as an additional cell is created which will be")
#     print("Included in all simulation runs. Therefore change this such that the cell is deleted afterwards or ")
#     print("comment out the line again.")
#     x = get_feasible_model_params().x
#     y_new = hay_objective_function(x)
#     y = get_feasible_model_objectives().y
#     try:
#         assert max(np.abs((y - y_new[y.index].values))) < 0.05
#     except:
#         print(y)
#         print(y_new[y.index].values)
#         raise