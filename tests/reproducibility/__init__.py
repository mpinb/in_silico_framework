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
import sys

def init_backwards_compatibility():
    """Function that sets attributes that are removed from ISF, but are useful for testing backwards
    compatibility, without having to refactor the entire test suite.

    Ideally, this should not be necessary, and the test suite should not rely on older functionality.
    However, for testing reproducibility, it can be of great interest to keep thins _exactly_ as they were.
    """

    # This cell modify function has since been removed, but is still useful for reproducibility tests.
    from tests.reproducibility import scale_apical_morph_86
    sys.modules["single_cell_parser.cell_modify_functions.scale_apical_morph_86"] = scale_apical_morph_86