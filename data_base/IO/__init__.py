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
"""Read and write data.

This subpackage provides the :mod:`~data_base.IO.LoaderDumper` subpackage to read and write data
in various file formats and data types.
"""

import logging
import sys
sys.modules['isf_data_base.IO'] = sys.modules[__name__]

logger = logging.getLogger("ISF").getChild(__name__)
