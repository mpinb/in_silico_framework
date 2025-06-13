# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.
"""
A Python translation of the setup for in silico current injection experiments as described in :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`.
"""

from __future__ import absolute_import

import os
from functools import partial

import numpy as np
from toolz.dicttoolz import merge

import single_cell_parser as scp

from .. import setup_stim
from ..combiner import Combiner
from ..evaluator import Evaluator
from ..L5tt_parameter_setup import (
    get_L5tt_template,
    get_L5tt_template_v2,
    set_ephys,
    set_hot_zone,
    set_many_param,
    set_morphology,
    set_param,
)
from ..parameters import param_to_kwargs, set_fixed_params
from ..simulator import Simulator, run_fun
from ..utils import tVec, vmApical, vmMax, vmSoma
from . import evaluation
from .specification import (
    get_hay_params_pdf,
    get_hay_param_names,
    get_hay_objective_names,
    get_feasible_model_params,
    get_feasible_model_objectives,
    get_hay_problem_description,
)

__author__ = "Arco Bast"
__date__ = "2018-11-08"


def record_bAP(cell, recSite1=None, recSite2=None):
    """Extract the voltage traces from the soma and two apical dendritic locations.

    This is used to quantify the voltage trace of a backpropagating AP (bAP)
    stimulus in a pyramidal neuron. The two apical recording sites are used
    to calculate e.g. backpropagating attenuation.

    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        recSite1 (float): The distance (um) from the soma to the first recording site.
        recSite2 (float): The distance (um) from the soma to the second recording site.

    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    assert recSite1 is not None
    assert recSite2 is not None
    return {
        "tVec": tVec(cell),
        "vList": (vmSoma(cell), vmApical(cell, recSite1), vmApical(cell, recSite2)),
        "vMax": vmMax(cell),
    }


def record_BAC(cell, recSite=None):
    """Extract the voltage traces from the soma and an apical dendritic location.

    This is used to quantify the voltage trace of a bAP-Activated Ca2+ (BAC) stimulus

    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        recSite (float): The distance (um) from the soma to the apical recording site.

    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    return {
        "tVec": tVec(cell),
        "vList": (vmSoma(cell), vmApical(cell, recSite)),
        "vMax": vmMax(cell),
    }


def record_Step(cell):
    """Extract the voltage trace from the soma.

    This is used to quantify the response of the cell to step currents.

    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.

    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    return {"tVec": tVec(cell), "vList": [vmSoma(cell)], "vMax": vmMax(cell)}


def get_Simulator(fixed_params, step=False, vInit=False):
    """Get a set up :py:class:`~biophysics_fitting.simulator.Simulator` object for the Hay protocol.

    Given cell-specific fixed parameters, set up a simulator object for the Hay protocol,
    including measuring functions for bAP and BAC stimuli (no step currents)

    Args:
        fixed_params (dict): A dictionary of fixed parameters for the cell.
        step (bool): Whether to include step current measurements. These take quite long to simulate. Default: ``False``.
        vInit (bool): Whether to include vInit measurements. (not implemented yet)

    Returns:
        :py:class:`~biophysics_fitting.simulator.Simulator`: A simulator object.

    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    s = Simulator()
    s.setup.stim_response_measure_funs = []
    s.setup.cell_param_generator = get_L5tt_template
    s.setup.params_modify_funs.append(
        ["fixed_params", partial(set_fixed_params, fixed_params=fixed_params)]
    )
    s.setup.cell_param_modify_funs.append(
        ["morphology", param_to_kwargs(set_morphology)]
    )
    s.setup.cell_param_modify_funs.append(["ephys", set_ephys])
    s.setup.cell_param_modify_funs.append(["params", set_param])
    s.setup.cell_param_modify_funs.append(["many_params", set_many_param])

    s.setup.cell_param_modify_funs.append(["hot_zone", param_to_kwargs(set_hot_zone)])
    s.setup.cell_generator = scp.create_cell
    # s.setup.cell_modify_funs.append('apical_dendrite_scaling', apical_dendrite_scaling)

    # --- Stimulus setup functions
    s.setup.stim_setup_funs.append(["bAP.stim", param_to_kwargs(setup_stim.setup_bAP)])
    s.setup.stim_setup_funs.append(["BAC.stim", param_to_kwargs(setup_stim.setup_BAC)])
    if step:
        s.setup.stim_setup_funs.append(
            ["StepOne.stim", param_to_kwargs(setup_stim.setup_StepOne)]
        )
        s.setup.stim_setup_funs.append(
            ["StepTwo.stim", param_to_kwargs(setup_stim.setup_StepTwo)]
        )
        s.setup.stim_setup_funs.append(
            ["StepThree.stim", param_to_kwargs(setup_stim.setup_StepThree)]
        )

    # --- Stimulus run functions
    ## bAP and BAC
    run_fun_bAP_BAC = partial(
        run_fun,
        T=34.0,
        Vinit=-75.0,
        dt=0.025,
        recordingSites=[],
        tStart=0.0,
        tStop=600.0,
        vardt=True,
    )
    s.setup.stim_run_funs.append(["bAP.run", param_to_kwargs(run_fun_bAP_BAC)])
    s.setup.stim_run_funs.append(["BAC.run", param_to_kwargs(run_fun_bAP_BAC)])

    ## Step currents
    run_fun_Step = partial(
        run_fun,
        T=34.0,
        Vinit=-75.0,
        dt=0.025,
        recordingSites=[],
        tStart=0.0,
        tStop=3000.0,
        vardt=True,
    )

    if step:
        s.setup.stim_run_funs.append(["StepOne.run", param_to_kwargs(run_fun_Step)])
        s.setup.stim_run_funs.append(["StepTwo.run", param_to_kwargs(run_fun_Step)])
        s.setup.stim_run_funs.append(["StepThree.run", param_to_kwargs(run_fun_Step)])
    s.setup.stim_response_measure_funs.append(
        ["bAP.hay_measure", param_to_kwargs(record_bAP)]
    )
    s.setup.stim_response_measure_funs.append(
        ["BAC.hay_measure", param_to_kwargs(record_BAC)]
    )
    if step:
        s.setup.stim_response_measure_funs.append(
            ["StepOne.hay_measure", param_to_kwargs(record_Step)]
        )
        s.setup.stim_response_measure_funs.append(
            ["StepTwo.hay_measure", param_to_kwargs(record_Step)]
        )
        s.setup.stim_response_measure_funs.append(
            ["StepThree.hay_measure", param_to_kwargs(record_Step)]
        )
    if vInit:
        raise NotImplementedError
    return s


def interpolate_vt(voltage_trace_):
    """Interpolate a voltage trace so that is has fixed time interval

    The NEURON simulator allows for a variable time step, which can make
    comparing voltage traces difficult. This function interpolates the voltage
    traces so that they have a fixed time interval of 0.025 ms.

    Args:
        voltage_trace_ (dict): A dictionary of voltage traces.

    Returns:
        dict: A dictionary of voltage traces with a fixed time interval.
    """
    out = {}
    for k in voltage_trace_:
        t = voltage_trace_[k]["tVec"]
        t_new = np.arange(0, max(t), 0.025)
        vList_new = [
            np.interp(t_new, t, v) for v in voltage_trace_[k]["vList"]
        ]  # I.np.interp
        out[k] = {"tVec": t_new, "vList": vList_new}
        if "iList" in voltage_trace_[k]:
            iList_new = [np.interp(t_new, t, i) for i in voltage_trace_[k]["iList"]]
            out[k] = {"tVec": t_new, "vList": vList_new, "iList": iList_new}
    return out


def map_truefalse_to_str(dict_):
    """Convert True/False to 'True'/'False' in a dictionary

    Args:
        dict_ (dict): A dictionary with boolean values.

    Returns:
        dict: A dictionary with boolean values converted to strings.
    """

    def _helper(x):
        if (x is True) or (x is np.True_):
            return "True"
        elif (x is False) or (x is np.False_):
            return "False"
        else:
            return x

    return {k: _helper(dict_[k]) for k in dict_}


def get_Evaluator(
    step=False,
    vInit=False,
    bAP_kwargs={},
    BAC_kwargs={},
    StepOne_kwargs={},
    StepTwo_kwargs={},
    StepThree_kwargs={},
    interpolate_voltage_trace=True,
):
    """Get a :py:class:`~biophysics_fitting.evaluator.Evaluator` object for the Hay protocol.

    Sets up an evaluator object for the Hay protocol, including measuring functions for bAP, BAC and three step current stimuli.

    Args:
        step (bool): Whether to include step current measurements (not implemented yet).
        vInit (bool): Whether to include vInit measurements. (not implemented yet)
        bAP_kwargs (dict): Keyword arguments for the ``bAP`` measurement function.
        BAC_kwargs (dict): Keyword arguments for the ``BAC`` measurement function.
        StepOne_kwargs (dict): Keyword arguments for the ``StepOne`` measurement function.
        StepTwo_kwargs (dict): Keyword arguments for the ``StepTwo`` measurement function.
        StepThree_kwargs (dict): Keyword arguments for the ``StepThree`` measurement function.
        interpolate_voltage_trace (bool): Whether to interpolate the voltage trace to a fixed time interval.

    Returns:
        :py:class:`~biophysics_fitting.evaluator.Evaluator`: An evaluator object.

    Raises:
        NotImplementedError: If :paramref:vInit is set to True.

    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    e = Evaluator()
    bap = evaluation.bAP(**bAP_kwargs)
    bac = evaluation.BAC(**BAC_kwargs)

    if interpolate_voltage_trace:
        e.setup.pre_funs.append(interpolate_vt)

    e.setup.evaluate_funs.append(["BAC.hay_measure", bac.get, "BAC.hay_features"])

    e.setup.evaluate_funs.append(["bAP.hay_measure", bap.get, "bAP.hay_features"])

    if step:
        step_one = evaluation.StepOne(**StepOne_kwargs)
        step_two = evaluation.StepTwo(**StepTwo_kwargs)
        step_three = evaluation.StepThree(**StepThree_kwargs)
        e.setup.evaluate_funs.append(
            ["StepOne.hay_measure", step_one.get, "StepOne.hay_features"]
        )
        e.setup.evaluate_funs.append(
            ["StepTwo.hay_measure", step_two.get, "StepTwo.hay_features"]
        )
        e.setup.evaluate_funs.append(
            ["StepThree.hay_measure", step_three.get, "StepThree.hay_features"]
        )
    if vInit:
        raise NotImplementedError
    e.setup.finalize_funs.append(lambda x: merge(list(x.values())))
    e.setup.finalize_funs.append(map_truefalse_to_str)

    return e


def get_Combiner(step=False, include_DI3=True):
    """Get a set up :py:class:`~biophysics_fitting.combiner.Combiner` object for the Hay protocol.

    Args:
        step (bool): Whether to include step current measurements.
        include_DI3 (bool):
            Whether to include the doublet ISI for the Step3 protocol in the step current measurements.
            Default: ``True``.

    Returns:
        :py:class:`~biophysics_fitting.combiner.Combiner`: A combiner object.

    See also:
        See :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for more information.
    """
    # up to 20220325, DI3 has not been included and was not in the fit_features file.
    c = Combiner()
    c.setup.append(
        "bAP_somatic_spike", ["bAP_APwidth", "bAP_APheight", "bAP_spikecount"]
    )
    c.setup.append("bAP", ["bAP_att2", "bAP_att3"])
    c.setup.append("BAC_somatic", ["BAC_ahpdepth", "BAC_APheight", "BAC_ISI"])
    c.setup.append("BAC_caSpike", ["BAC_caSpike_height", "BAC_caSpike_width"])
    c.setup.append("BAC_spikecount", ["BAC_spikecount"])
    if step:
        c.setup.append("step_mean_frequency", ["mf1", "mf2", "mf3"])
        c.setup.append(
            "step_AI_ISIcv", ["AI1", "AI2", "ISIcv1", "ISIcv2", "AI3", "ISIcv3"]
        )
        if include_DI3:
            c.setup.append("step_doublet_ISI", ["DI1", "DI2", "DI3"])
        else:
            c.setup.append("step_doublet_ISI", ["DI1", "DI2"])
        c.setup.append("step_AP_height", ["APh1", "APh2", "APh3"])
        c.setup.append("step_time_to_first_spike", ["TTFS1", "TTFS2", "TTFS3"])
        c.setup.append(
            "step_AHP_depth",
            ["fAHPd1", "fAHPd2", "fAHPd3", "sAHPd1", "sAHPd2", "sAHPd3"],
        )
        c.setup.append("step_AHP_slow_time", ["sAHPt1", "sAHPt2", "sAHPt3"])
        c.setup.append("step_AP_width", ["APw1", "APw2", "APw3"])
    c.setup.combinefun = np.max
    return c


def get_fixed_params_example():
    """Get an example of cell-specific fixed params.

    Fixed parameters are parameters that are required for a stimulus protocol.
    They are specific to a stimulus protocol, and to the morphology of the cell.
    This method provides an example of such fixed parameters for a L5PT and the
    bAP and BAC stimuli.

    Returns:
        dict: A dictionary with the fixed parameters.
    """
    morphology_fn = os.path.abspath(
        os.path.join(
            __file__,
            "..",
            "..",
            "getting_started",
            "example_data",
            "morphology",
            "89_L5_CDK20050712_nr6L5B_dend_PC_neuron_transform_registered_C2.hoc",
        )
    )
    fixed_params = {
        "hot_zone.max_": 614,
        "hot_zone.min_": 414,
        "bAP.hay_measure.recSite1": 349,
        "bAP.hay_measure.recSite2": 529,
        "BAC.stim.dist": 349,
        "BAC.hay_measure.recSite": 349,
        "morphology.filename": morphology_fn,
    }
    return fixed_params
