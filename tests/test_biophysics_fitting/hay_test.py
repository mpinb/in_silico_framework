import neuron
import numpy as np
import pytest

import mechanisms.l5pt
from biophysics_fitting.hay_complete_default_setup import (
    get_Evaluator as get_hay_Evaluator,
)
from biophysics_fitting.hay_complete_default_setup import (
    get_feasible_model_objectives,
    get_feasible_model_params,
)
from biophysics_fitting.hay_complete_default_setup_python import get_Combiner
from biophysics_fitting.hay_complete_default_setup_python import (
    get_Evaluator as get_python_evaluator,
)
from biophysics_fitting.hay_evaluation import hay_objective_function
from tests.test_biophysics_fitting import (
    deserialize_voltage_traces,
    get_example_models_89,
    get_test_simulator_89,
    serialize_voltage_traces,
)

h = neuron.h


def test_simulator_89(request, step=True):
    """Run an ISF simulator on working biophysical parameters for morphology 89"""
    s = get_test_simulator_89(step=step)
    p = get_example_models_89().iloc[0]  # just a random working model
    v = s.run(p)

    # save in cache for evaluation tests
    request.config.cache.set("shared_voltage_traces", serialize_voltage_traces(v))


def test_hay_evaluation_python(request, step=True):
    """Test the evaluation of the Python hay evaluator translation"""

    voltage_traces = request.config.cache.get("shared_voltage_traces", None)
    assert (
        voltage_traces is not None
    ), "The voltage traces should be set in pytest scope by now. Is the test dependency correctly configured?"
    voltage_traces = deserialize_voltage_traces(voltage_traces)

    e = get_python_evaluator(step=step)
    evaluation = e.evaluate(voltage_traces)

    # test if results are within bounds, which they should
    evaluation = get_Combiner(step=step).combine(evaluation)
    for stim, ev in evaluation.items():
        cutoff = 4.5 if "step" in stim.lower() else 3.2
        assert ev < cutoff, "Sigma cuttof of {} for {} exceeded: {}".format(
            cutoff, stim, ev
        )


def test_hay_evaluation_python_compatibility(request):
    """test if new python translation of hay's hoc code provides the same results"""
    zero_tolerance = 1e-10
    v = request.config.cache.get("shared_voltage_traces", None)
    v = deserialize_voltage_traces(v)

    evaluation_python_translation = get_python_evaluator(
        step=False, interpolate_voltage_trace=False
    ).evaluate(v)

    evaluation_hay = get_hay_Evaluator(
        step=False, interpolate_voltage_trace=False
    ).evaluate(v)

    diff = {
        k: evaluation_python_translation[k] - evaluation_hay[k] for k in evaluation_hay
    }

    for ev, obj_d in diff.items():
        assert (
            np.abs(obj_d) < 1e-10
        ), "{stim} is off by more than just a numerical truncation factor: {rd}".format(
            stim=ev, rd=obj_d
        )


@pytest.mark.skip(reason="Thist test segfaults on distributed pytest workers, despite importing mechanisms.")
def test_original_hay_evaluation():
    """compare the result of the optimization of the hay evaluator with a precomputed result

    This calls hay_objective_function, which calls evaluator.evaluate_population
    During this procedure, NEURON tries to access a dendrite which has been deleted, resulting
    in a segfault.
    Is this due to the way GAcell_v3 is set up? Is this a stump cell without dendries?
    # TODO: test with GAcell_v2 or other cells.
    """
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

    import mechanisms.l5pt

    x = get_feasible_model_params().x
    v_len = 32
    assert len(x) == v_len, "The parameter vector for the original hay evaluator needs to be {}".format(v_len)
    y_new = hay_objective_function(x)
    y = get_feasible_model_objectives().y
    try:
        assert max(np.abs((y - y_new[y.index].values))) < 0.05
    except:
        print(y)
        print(y_new[y.index].values)
        raise
