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

"""
This directory contains the `.mod` files that define the biophysical behaviour of ion channels found in a Layer 5 Pyramidal Tract neuron (L5PT).
In addition, it contains network connectivity parameters that define synaptic connections.

"""

import os, platform, six, neuron, glob
from config.isf_logging import logger, stream_to_logger

try:
    import tables
except ImportError:
    pass

parent = os.path.abspath(os.path.dirname(__file__))
arch = [platform.machine(), 'i686', 'x86_64', 'powerpc', 'umac']
channels = 'channels_py2' if six.PY2 else 'channels_py3'
netcon = 'netcon_py2' if six.PY2 else 'netcon_py3'
channels_path = os.path.join(parent, channels)
netcon_path = os.path.join(parent, netcon)

def check_nrnivmodl_is_available():
    """
    Check if nrnivmodl is available in the PATH.
    """
    try:
        os.system('which nrnivmodl')
        return True
    except Exception as e:
        logger.error("nrnivmodl is not available in the PATH. Please add it to your PATH.")
        raise e

def check_if_mechanisms_are_compiled(path):
    if os.name == 'nt':
        return any(glob.glob(os.path.join(path, '*.dll')))
    else:
        return any([os.path.exists(os.path.join(path, a, '.libs')) for a in arch])

def compile_mechanisms(path):
    """
    Compile the mechanisms in the given path using nrnivmodl.
    This function is only needed if the mechanisms are not already compiled.
    """
    if os.name == 'nt': # windows
        os.system('cd /d "{}" && nrnivmodl'.format(path))
    else: # unix
        os.system('(cd "{}"; nrnivmodl)'.format(path))


assert check_nrnivmodl_is_available(), "nrnivmodl is not available in the PATH. Please add it to your PATH."

if not check_if_mechanisms_are_compiled(channels_path) \
    or not check_if_mechanisms_are_compiled(netcon_path):
    logger.warning("Neuron mechanisms are not compiled. Attempting automatic compilation.")

    compile_mechanisms(channels_path)
    compile_mechanisms(netcon_path)

    try:
        assert check_if_mechanisms_are_compiled(channels_path)
        assert check_if_mechanisms_are_compiled(netcon_path)
    except AssertionError as e:
        raise UserWarning("Could not compile mechanisms. Please do it manually") from e

try:
    with stream_to_logger(logger=logger):
        logger.info("Loading mechanisms in NEURON namespace...")
        mechanisms_loaded = neuron.load_mechanisms(channels_path)
        netcon_loaded = neuron.load_mechanisms(netcon_path)
    assert mechanisms_loaded, "Couldn't load mechanisms."
    assert netcon_loaded, "Couldn't load netcon"
except Exception as e:
     raise e