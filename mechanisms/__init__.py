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
This directory contains the `.mod` files that define the biophysical behaviour of ion channels found in a Layer 5 Pyramidal Tract neuron (L5PT).
In addition, it contains network connectivity parameters that define synaptic connections.

Importing this module on UNIX systems registers the mechanisms in NEURON namespace. 
This only works if they are compiled, which should have happened upon configuring ISF.
If this is not the case, you can:

.. code-block:: python

    >>> import mechanisms
    >>> mechanisms.are_compiled()  # check if all mechanisms are compiled
    False
    >>> mechanisms.compile_mechanisms(force_recompile=False)  # compile mechanisms if not already compiled
    >>> mechanisms.are_compiled()  # check if all mechanisms are compiled
    True

See also:
    :mod:`config.isf_configure`
"""

import os, platform, six, neuron, glob, shutil, subprocess, sys, threading
from pathlib import Path
import logging
logger = logging.getLogger("ISF").getChild(__name__) 
from config.isf_logging import stream_to_logger
import config
try: import tables
except ImportError: pass

MECHANISMS_PATH = Path(config.__file__).parent / "user" / "mechanisms"
CHANNELS_PATH = MECHANISMS_PATH / "channels"
NETCON_PATH = MECHANISMS_PATH / "netcon"
ARCHITECTURE = [platform.machine(), 'i686', 'x86_64', 'powerpc', 'umac']
MECH_LOCK = threading.Lock()

def check_nrnivmodl_is_available():
    """
    Check if nrnivmodl is available in the PATH.
    Cross-platform implementation that works on both Windows and Unix systems.
    """
    try:
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

def _check_if_mechanisms_are_compiled_at_path(path):
    if os.name == 'nt':
        return any(glob.glob(os.path.join(path, '*.dll')))
    else:
        arch = [platform.machine(), 'i686', 'x86_64', 'powerpc', 'umac']
        return any([os.path.exists(os.path.join(path, a, '.libs')) for a in arch])

def _compile_mechanisms_at_path(path):
    """
    Compile the mechanisms in the given path using nrnivmodl.
    """
    assert check_nrnivmodl_is_available(), "nrnivmodl is not available in the PATH. Please add it to your PATH."
    nrnivmodl_path = shutil.which('nrnivmodl')
    logger.info(f"Compiling mechanisms at {path} using {nrnivmodl_path}")
    user_inc_flags = os.environ.get("NRN_USER_INC_FLAGS", None)
    nrn_cmd = [nrnivmodl_path]
    if user_inc_flags is not None:
        nrn_cmd.append('-incflags')
        nrn_cmd.append(user_inc_flags)
    logger.info(f"nrnivmodl command: {nrn_cmd}")
    try:
        subprocess.check_output(nrn_cmd, cwd=path, env=os.environ.copy())
    except subprocess.CalledProcessError as e:
        print(e.output)
        raise e

def are_compiled():
    """
    Check if all mechanisms are compiled.
    """
    if os.name == 'nt':
        return all([any(glob.glob(os.path.join(path, '*.dll'))) for path in (CHANNELS_PATH, NETCON_PATH)])
    else:
        return all([
            _check_if_mechanisms_are_compiled_at_path(path) 
            for path in (CHANNELS_PATH, NETCON_PATH)
            ])

def are_loaded():
    """
    Check if all mechanisms are loaded into NEURON namespace.
    """
    return CHANNELS_PATH in neuron.nrn_dll_loaded and NETCON_PATH in neuron.nrn_dll_loaded
    # channels = _get_mechanism_names(channels_path)
    # netcons = _get_mechanism_names(netcon_path)
    # all_mechanisms = channels + netcons
    # return all(name in neuron.h.__dict__.keys() for name in all_mechanisms)

def list_loaded():
    return neuron.h.__dict__.keys()

def compile_mechanisms(force_recompile=False):
    """Compile the mechanisms for L5PTs.
    
    This function checks if the mechanisms are compiled at the specified paths, and (re)compiles them
    if necessary using ``nrnivmodl``.
    
    See also:
        :func:`check_nrnivmodl_is_available` to check if `nrnivmodl` is available in the ``PATH``, and
        :func:`_compile_mechanisms_at_path` to compile the mechanisms in a given directory.
        
    Args:
        force_recompile (bool): If True, forces recompilation of the mechanisms even if they are already compiled.
            Defaults to False.
            
    Raises:
        UserWarning: If the mechanisms needed to be compiled, but failed.
    """
    logger.info("Compiling mechanisms using the FLAGS flags: {}".format(
        ["{}: {}".format(e, os.environ.get(e)) for e in os.environ.keys() if "FLAGS" in e]))
    
    for path in (CHANNELS_PATH, NETCON_PATH):
        if not _check_if_mechanisms_are_compiled_at_path(path):
            _compile_mechanisms_at_path(path)
        elif force_recompile == True:
            logger.warning(f"Mechanisms already compiled at {path}. 'force_recompile' is set to True. Recompiling...")
            _compile_mechanisms_at_path(path)
            if not _check_if_mechanisms_are_compiled_at_path(path):
                raise UserWarning("Could not compile mechanisms. Please do it manually")
        else:
            logger.info(f"Mechanisms already compiled at {path} and 'force_recompile' is set to False. Skipping compilation.")

def load():
    """Load the mechanisms into NEURON namespace.
    
    Also implements a thread lock to avoid concurrent loading of shared objects or dynamically linked libraries.
    This is especially important on Windows, since DLLs are sensitive to concurrent loading.
    
    Raises:
        AssertionError: If the mechanisms could not be loaded.
    """
    try:
        with MECH_LOCK:  # Ensure thread safety when loading mechanisms
            with stream_to_logger(logger=logger):
                mechanisms_loaded = neuron.load_mechanisms(CHANNELS_PATH)
                netcon_loaded = neuron.load_mechanisms(NETCON_PATH)
            assert mechanisms_loaded, "Couldn't load mechanisms."
            assert netcon_loaded, "Couldn't load netcon"
            logger.info("Loaded mechanisms in NEURON namespace.")
    except Exception as e:
        raise e

# import trigger: emit warning if they are not compiled
# auto-add them to NEURON namespace if they are compiled
# This is similar to NEURON's autoload function, except that it's compatible with Windows and thread-safe.

if are_compiled():
    if not are_loaded():
        load()
else:
    logger.warning("Mechanisms are not compiled yet.")    
