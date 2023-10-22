from project_specific_ipynb_code.reduced_model_output_paper import PostCell
from model_data_base import utils
import os
import getting_started

getting_started_folder = getting_started.parent

n_cells = 1086
morph_lengths = {
    'CDK84': 30,
    'CDK85': 25,
    'CDK86': 32,
    'CDK89': 29,
    'CDK91': 26
}

cellParamName = os.path.join(getting_started_folder, \
                             'biophysical_constraints', \
                             '86_CDK_20041214_BAC_run5_soma_Hay2013_C2center_apic_rec.param')
networkName = os.path.join(getting_started_folder, \
                           'functional_constraints', \
                           'network.param')
example_path = os.path.join(getting_started_folder, \
                            'example_simulation_data', \
                            'C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center', \
                            '20150815-1530_20240', \
                            'simulation_run0000_synapses.csv')