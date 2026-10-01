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
Explore viable biophysical models from a given seedpoint.
Given the following empirical constraints:

- a set of biophysical parameters
- a morphology
- empirically recorded responses to defined stimulus protocols (see e.g. :func:`~biophysics_fitting.hay.specification.get_hay_problem_description`).

this package provides methods and full workflows that allow you to make random variations on the input biophysical parameters, 
run the stimulus protocols on the cell, and evaluate how much they deviate from the empirically recorded mean.
Eventually, this random walk through parameter space can explore very diverse biophysical models that are all within the empirical constraints.
"""
from .RW import RW
