import os
import neuron

h = neuron.h
from Interface import scp
from getting_started import getting_started_dir  # path to getting started folder
from model_data_base.utils import silence_stdout


def setup_current_injection_experiment(rangevars=[]):
    """Sets up a current injection experiment of some .hoc and .param file.
    The following parameters define the experiment:

    Returns:
        cell: a cell object that contains the simulation.
    """
    cell_param = os.path.join(getting_started_dir, \
                        'biophysical_constraints', \
                        '86_CDK_20041214_BAC_run5_soma_Hay2013_C2center_apic_rec.param')
    cell_param = scp.build_parameters(
        cell_param)  # this is the main method to load in parameterfiles
    # load scaled hoc morphology
    cell_param.neuron.filename = os.path.join(getting_started_dir, 'anatomical_constraints', \
                        '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2center_scaled_diameters.hoc')
    with silence_stdout:
        cell = scp.create_cell(cell_param.neuron)

    iclamp = h.IClamp(0.5, sec=cell.soma)
    iclamp.delay = 150  # give the cell time to reach steady state
    iclamp.dur = 5  # 5ms rectangular pulse
    iclamp.amp = 1.9  # 1.9 ?? todo ampere
    for rv in rangevars:
        cell.record_range_var(rv)

    scp.init_neuron_run(cell_param.sim, vardt=True)  # run the simulation

    return cell