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
Example configuration for generating neuron models.

This module provides example configuration and setup for simulating and evaluating biophysical models of Layer 5 Pyramidal Tract neurons according to the
methods described in :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011`, including:

- Neuron model parameter setup
- Target objectives
- Simulation setup
- Evaluation routines

While all of these components are usually defined by the user for use with either :mod:`~biophysics_fitting.optimizer` or :mod:`~biophysics_fitting.exploration_from_seedpoint`, 
it can be of use to see how this example is configured as reference material.
For example, the :class:`~biophysics_fitting.simulator.Simulator` can be relatively abstract, to allow for a lot of flexibility.
An example of how it is set up for L5PT neurons provides useful reference material to see what a :class:`~biophysics_fitting.simulator.Simulator` object can and should do.

See also:
    :meth:`~biophysics_fitting.hay.default_setup.get_Simulator` for an example setup of a :class:`~biophysics_fitting.simulator.Simulator` object.
"""