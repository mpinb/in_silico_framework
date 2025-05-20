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

import os, platform, six, neuron, glob, shutil, subprocess
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
    Cross-platform implementation that works on both Windows and Unix systems.
    """
    where_cmd = "which" if os.name != 'nt' else "where"
    try:
        result = subprocess.run(
            [where_cmd, 'nrnivmodl'], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True)
        if result.returncode == 0 and result.stdout.strip():
            logger.info(f"nrnivmodl found at: {result.stdout.strip()}")
            return True
        else:
            path = shutil.which('nrnivmodl')
            if path:
                logger.info(f"nrnivmodl found at: {path}")
                return True
            logger.error("nrnivmodl not found in PATH")
            return False
    except Exception as e:
        logger.error(f"Error checking nrnivmodl availability: {str(e)}")
        logger.error("nrnivmodl is not available in the PATH. Please add it to your PATH.")
        raise

def check_if_mechanisms_are_compiled(path):
    if os.name == 'nt':
        return any(glob.glob(os.path.join(path, '*.dll')))
    else:
        return any([os.path.exists(os.path.join(path, a, '.libs')) for a in arch])

def _compile_mechanisms_at_path(path):
    """
    Compile the mechanisms in the given path using nrnivmodl.
    This function is only needed if the mechanisms are not already compiled.
    """
    subprocess.run(['nrnivmodl'], cwd=path, check=True)

def compile_l5pt_mechanisms(force_recompile=False):
    """
    Compile the mechanisms in the local directory.
    This function is only needed if the mechanisms are not already compiled.
    """
    for path in (channels_path, netcon_path):
        if not check_if_mechanisms_are_compiled(path) or force_recompile:
            _compile_mechanisms_at_path(path)
            if not check_if_mechanisms_are_compiled(path):
                raise UserWarning("Could not compile mechanisms. Please do it manually")

assert check_nrnivmodl_is_available(), "nrnivmodl is not available in the PATH. Please add it to your PATH."

compile_l5pt_mechanisms(force_recompile=False)

try:
    with stream_to_logger(logger=logger):
        logger.info("Loading mechanisms in NEURON namespace...")
        mechanisms_loaded = neuron.load_mechanisms(channels_path)
        netcon_loaded = neuron.load_mechanisms(netcon_path)
    assert mechanisms_loaded, "Couldn't load mechanisms."
    assert netcon_loaded, "Couldn't load netcon"
except Exception as e:
    raise e