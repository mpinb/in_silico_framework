"""
:skip-doc:

TODO: adapt this to be more general
"""
import sys
import os.path

whiskers = ['B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'D3']
#whiskers = ['B1','B2','B3','C1','C2','C3','D1','D2','D3','E2']
#whiskers = ['B1','B2','B3','C1','C3','D1','D2','D3','E2']
#cellLocations = ['B1border','B2border','B3border','C1border',\
cellLocations = ['B1border','B2border','B3border','C1border','C2center',\
                'C3border','D1border','D2border','D3border']

pythonScriptName = '~/project_src/NeuroSim/functional_network_assembly/ongoing_network_param_from_template.py'
locationBaseName = '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/L5tt/network_embedding/postsynaptic_location/3x3_C2_sampling'
locationFolderNames = {'B1border': '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2_B1border_synapses_20150504-1602_10393',\
                        'B2border': '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2_B2border_synapses_20150504-2001_11709',\
                        'B3border': '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2_B3border_synapses_20150504-1959_11710',\
                        'C1border': '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2_C1border_synapses_20150504-1606_10377',\
                        'C2center': '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2center_synapses_20150504-1611_10389',\
                        'C3border': '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2_C3border_synapses_20150504-1602_10391',\
                        'D1border': '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2_D1border_synapses_20150504-1612_10395',\
                        'D2border': '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2_D2border_synapses_20150504-1629_10397',\
                        'D3border': '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2_D3border_synapses_20150504-1630_10399'}

synParamName = '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/L5tt/ongoing_activity/'
synParamName += 'ongoing_activity_celltype_template_exc_conductances_fitted_NMDA_decay65.0_amp0.6.param'
#synParamName = '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/L5tt/ongoing_activity/ongoing_activity_celltype_template_exc_conductances_fitted_dynamic_syns.param'
outPath = '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/L5tt/ongoing_activity/'


def create_param_file_script(fname, outName):
    if not fname.endswith('.sh'):
        fname += '.sh'
    with open(fname, 'w') as scriptFile:
        header = '#!/bin/bash\n\n'
        scriptFile.write(header)
        for cellLocation in cellLocations:
            line = 'python '
            line += pythonScriptName
            line += ' '
            line += synParamName
            line += ' '
            line += os.path.join(locationBaseName, cellLocation,
                                 locationFolderNames[cellLocation],
                                 'NumberOfConnectedCells.csv')
            line += ' '
            line += os.path.join(locationBaseName, cellLocation,
                                 locationFolderNames[cellLocation],
                                 locationFolderNames[cellLocation])
            line += '.syn'
            #                line += ' '
            #                line += whisker
            # output name
            line += ' '
            line += outPath
            #                line += whisker
            #                line += '_'
            line += outName
            line += '_'
            line += cellLocation
            line += '.param\n'
            scriptFile.write(line)


if __name__ == '__main__':
    scriptName = sys.argv[1]
    paramName = sys.argv[2]
    create_param_file_script(scriptName, paramName)
