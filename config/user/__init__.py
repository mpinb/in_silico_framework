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
User-specific configuration

These configuration modules allow the user to set per-project configuration. 
These are ideally set once for a specific project, and left unchanged after that.

Beware when relying on default fallback values, as it makes your code less explicit.
It is always recommended to explicitly pass your data sources to the relevant workflows, 
rather than relying on some default fallback values set here.
"""