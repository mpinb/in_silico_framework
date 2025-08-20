import neuron

import mechanisms.l5pt
from biophysics_fitting.hay.default_setup import get_Combiner
from biophysics_fitting.hay.default_setup import (
    get_Evaluator as get_python_evaluator,
)
from tests.test_biophysics_fitting import (
    get_example_models_89,
    get_test_simulator_89,
)

h = neuron.h

def test_hay_simulation_evaluation(step=True):
    """Test the evaluation of the Python hay evaluator translation"""

    # test simulation
    s = get_test_simulator_89(step=step)
    known_working_parameters = get_example_models_89().iloc[0]  # just a random working model
    voltage_traces = s.run(known_working_parameters)

    # test evaluation
    e = get_python_evaluator(step=step)
    evaluation = e.evaluate(voltage_traces)
    evaluation = get_Combiner(step=step).combine(evaluation)
    for stim, ev in evaluation.items():
        cutoff = 4.5 if "step" in stim.lower() else 3.2
        assert ev < cutoff, "Sigma cuttof of {} for {} exceeded: {}".format(
            cutoff, stim, ev
        )

if __name__ == "__main__":
    test_hay_simulation_evaluation(step=True)