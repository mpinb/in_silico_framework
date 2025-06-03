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

Importing this module on UNIX systems registers the mechanisms in NEURON namespace. 
This only works if they are compiled, which should have happened upon configuring ISF.
If this is not the case, you can:

```python
from mechanisms.l5pt import compile_l5pt_mechanisms, load_mechanisms, check_if_all_mechanisms_are_compiled, check_if_all_mechanisms_are_loaded
compile_l5pt_mechanisms(force_recompile=False)  # compile mechanisms if not already compiled
check_if_all_mechanisms_are_compiled()  # check if all mechanisms are compiled
```

Attention:
    Importing this module on Windows systems does not automatically register the mechanisms in NEURON namespace.
    Windows uses `spawn` instead of `fork` to create new processes, which means that the NEURON namespace is not shared between the parent and child processes.
    This has as a consequence that multiple subprocesses need to reload mechanisms simultaneously, creating race conditions between processes.
    To load mechanisms on Windows, you need to explicitly call the `load_mechanisms()` function after compiling them::
    
    ```python
    from mechanisms.l5pt import load_mechanisms
    load_mechanisms()  # load mechanisms into NEURON namespace

See also:
    :py:mod:`config.isf_configure`
"""

import os, platform, six, neuron, glob, shutil, subprocess, sys, threading
import logging
logger = logging.getLogger("ISF").getChild(__name__) 
from config.isf_logging import stream_to_logger
try: import tables
except ImportError: pass

parent = os.path.abspath(os.path.dirname(__file__))
channels_path = os.path.join(parent, 'channels_py2' if six.PY2 else 'channels_py3')
netcon_path = os.path.join(parent, 'netcon_py2' if six.PY2 else 'netcon_py3')
arch = [platform.machine(), 'i686', 'x86_64', 'powerpc', 'umac']
mech_lock = threading.Lock()

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
    subprocess.run([nrnivmodl_path], cwd=path, check=True, env=os.environ.copy())

def are_compiled():
    """
    Check if all mechanisms are compiled.
    """
    if os.name == 'nt':
        return all([any(glob.glob(os.path.join(path, '*.dll'))) for path in (channels_path, netcon_path)])
    else:
        return all([
            _check_if_mechanisms_are_compiled_at_path(path) 
            for path in (channels_path, netcon_path)
            ])

def are_loaded():
    """
    Check if all mechanisms are loaded into NEURON namespace.
    """
    return channels_path in neuron.nrn_dll_loaded and netcon_path in neuron.nrn_dll_loaded
    # channels = _get_mechanism_names(channels_path)
    # netcons = _get_mechanism_names(netcon_path)
    # all_mechanisms = channels + netcons
    # return all(name in neuron.h.__dict__.keys() for name in all_mechanisms)

def compile_mechanisms(force_recompile=False):
    """Compile the mechanisms for L5PTs.
    
    This function checks if the mechanisms are compiled at the specified paths, and (re)compiles them
    if necessary using ``nrnivmodl``.
    
    See also:
        :py:func:`check_nrnivmodl_is_available` to check if `nrnivmodl` is available in the ``PATH``, and
        :py:func:`_compile_mechanisms_at_path` to compile the mechanisms in a given directory.
        
    Args:
        force_recompile (bool): If True, forces recompilation of the mechanisms even if they are already compiled.
            Defaults to False.
            
    Raises:
        UserWarning: If the mechanisms needed to be compiled, but failed.
    """
    for path in (channels_path, netcon_path):
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
        with mech_lock:  # Ensure thread safety when loading mechanisms
            with stream_to_logger(logger=logger):
                mechanisms_loaded = neuron.load_mechanisms(channels_path)
                netcon_loaded = neuron.load_mechanisms(netcon_path)
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
    logger.warning("Mechanisms are not compiled. Please configure ISF to compile them, or run `compile()` manually.")    
