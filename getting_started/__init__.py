from __future__ import print_function
import os

getting_started_dir = parent = os.path.abspath(os.path.dirname(__file__))


def generate_param_files_with_valid_references():
    IN_SILICO_FRAMEWORK_DIR = os.path.abspath(
        os.path.dirname(os.path.dirname(__file__)))
    suffix = '.TEMPLATE'
    filelist = ['getting_started/biophysical_constraints/86_CDK_20041214_BAC_run5_soma_Hay2013_C2center_apic_rec.param.TEMPLATE', \
                'getting_started/functional_constraints/network.param.TEMPLATE', \
                'getting_started/example_simulation_data/C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center/20150815-1530_20240/20240_network_model.param.TEMPLATE',\
                'getting_started/example_simulation_data/C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center/20150815-1530_20240/20240_neuron_model.param.TEMPLATE']
    for path in filelist:
        path = os.path.join(IN_SILICO_FRAMEWORK_DIR, path)
        assert os.path.exists(path)
        assert path.endswith(suffix)
        with open(path, 'r') as in_, open(path.rstrip(suffix), 'w') as out_:
            out_.write(in_.read().replace('[IN_SILICO_FRAMEWORK_DIR]',
                                          IN_SILICO_FRAMEWORK_DIR))
            #for line in in_.readlines():
            #    line = line
            #    print(line, file = out_)


generate_param_files_with_valid_references()

hocfile = os.path.join(
    getting_started_dir,
    'anatomical_constraints/86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2center_scaled_diameters.hoc'
)
networkParam = os.path.join(getting_started_dir,
                            'functional_constraints/network.param')
neuronParam = os.path.join(
    getting_started_dir,
    'biophysical_constraints/86_CDK_20041214_BAC_run5_soma_Hay2013_C2center_apic_rec.param'
)
radiiData = os.path.join(getting_started_dir, 'radii', 'data')
