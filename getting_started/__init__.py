# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import os, logging
logger = logging.getLogger("ISF").getChild(__name__)

getting_started_dir = parent = os.path.abspath(os.path.dirname(__file__))
example_data_dir = os.path.join(getting_started_dir, 'example_data')
tutorial_output_dir = os.path.join(os.environ.get("HOME"), 'ISF_tutorial_output')

IN_SILICO_FRAMEWORK_DIR = os.path.abspath(
    os.path.dirname(os.path.dirname(__file__)))
TEMPLATE_FILES = [
    os.path.join(example_data_dir, e) for e in (
        'biophysical_constraints/86_C2_center.param.TEMPLATE',
        'functional_constraints/network.param.TEMPLATE',
        'simulation_data/C2_center_example/20240_network_model.param.TEMPLATE',
        'simulation_data/C2_center_example/20240_neuron_model.param.TEMPLATE',
        'simulation_data/C2_center_example_subsampled/20240_neuron_model.param.TEMPLATE',
        'simulation_data/C2_center_example_subsampled/20240_network_model.param.TEMPLATE',
    )]

def generate_param_files_with_valid_references(overwrite_param_files=False):
    """Generate parameter files with valid references to the In Silico Framework directory.
    
    This function replaces the placeholder [IN_SILICO_FRAMEWORK_DIR] in the template files
    to resolved paths on the filesystem.
    This configuration function is run once after installing ISF.
    
    See also:
        :mod:`config.isf_configure` for configuring ISF for your local system.
    """
    suffix = '.TEMPLATE'
    for template_path in TEMPLATE_FILES:
        template_path = os.path.join(IN_SILICO_FRAMEWORK_DIR, template_path)
        assert os.path.exists(template_path)
        assert template_path.endswith(suffix)
        target_path = os.path.join(IN_SILICO_FRAMEWORK_DIR, template_path.rstrip(suffix))
        if os.path.exists(target_path):
            if overwrite_param_files:
                logger.info(f"Overwriting {target_path}.")
            else:
                logger.debug(f"File {target_path} already exists and 'overwrite_param_files' is False. Skipping.")
                continue
        
        with open(template_path, 'r') as in_, open(target_path, 'w') as out_:
            out_.write(in_.read().replace(
                '[IN_SILICO_FRAMEWORK_DIR]',
                IN_SILICO_FRAMEWORK_DIR))
            #for line in in_.readlines():
            #    line = line
            #    print(line, file = out_)


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
