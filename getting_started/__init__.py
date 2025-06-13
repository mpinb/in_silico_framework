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

from __future__ import print_function
import os

getting_started_dir = parent = os.path.abspath(os.path.dirname(__file__))
example_data_dir = os.path.join(getting_started_dir, 'example_data')
tutorial_output_dir = os.path.join(os.environ.get("HOME"), 'ISF_tutorial_output')


def generate_param_files_with_valid_references():
    IN_SILICO_FRAMEWORK_DIR = os.path.abspath(
        os.path.dirname(os.path.dirname(__file__)))
    suffix = '.TEMPLATE'
    filelist = [os.path.join(example_data_dir, e) for e in (
                'biophysical_constraints/86_C2_center.param.TEMPLATE', \
                'functional_constraints/network.param.TEMPLATE', \
                'simulation_data/C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center/20150815-1530_20240/20240_network_model.param.TEMPLATE',\
                'simulation_data/C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center/20150815-1530_20240/20240_neuron_model.param.TEMPLATE')]
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
    example_data_dir,
    'anatomical_constraints',
    '86_C2_center_scaled_diameters.hoc'
)
networkParam = os.path.join(
    example_data_dir,
    'functional_constraints',
    'network.param')

neuronParam = os.path.join(
    example_data_dir,
    'biophysical_constraints',
    '86_C2_center.param')

radiiData = os.path.join(
    example_data_dir, 
    'morphology')
