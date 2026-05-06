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
"""Default values for file locking.

This module allows the user to set default fallback values for file locking.
This default fallback value is only used when the env variable ``"ISF_DISTRIBUTED_LOCK_CONFIG"`` is unset.
It is recommended to make use of this env variable when setting up your environment, especially for HPC contexts.

For example, to use the zookeeper locking configuration:

- launch a zookeeper server
- write out the configuration for your session::

    config = [{
        'config': {
            'hosts': 'ip:port'
        },
        'type': 'zookeeper'
    }]

- set ``"ISF_DISTRIBUTED_LOCK_CONFIG"`` to the filepath pointing to this config file.
"""
DEFAULT_CONFIG = [
    dict(type="file"),
    # dict(type="redis", config=dict(host="spock", port=8885, socket_timeout=1)),
    # dict(type="redis", config=dict(host="localhost", port=6379, socket_timeout=1)),
]
"""Default fallback value when no file locking is configured. Defaults to file-based file locking."""

