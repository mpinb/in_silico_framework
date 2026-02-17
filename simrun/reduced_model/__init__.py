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

"""
From times where Arco used LDA to extract kernels.

However, this scratched the computational limits when trying to add spatial information. 
For this reason, this reduced modeling approach has been extended into :py:mod:`simrun.modular_reduced_model_inference`
so that it can be modularized and parallellized better.

:skip-doc:
"""