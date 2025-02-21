"""
This directory contains the `.mod` files that define the biophysical behaviour of ion channels found in a Layer 5 Pyramidal Tract neuron (L5PT).
In addition, it contains network connectivity parameters that define synaptic connections.

"""

import os, platform
from config.isf_logging import logger, stream_to_logger

try:
    import tables
except ImportError:
    pass

import neuron

parent = os.path.abspath(os.path.dirname(__file__))

arch = [platform.machine(), 'i686', 'x86_64', 'powerpc', 'umac']

import six
if six.PY2:
    channels = 'channels_py2'
    netcon = 'netcon_py2'
else:
    channels = 'channels_py3'
    netcon = 'netcon_py3'

try:
    assert any(
        [os.path.exists(os.path.join(parent, channels, a, '.libs')) for a in arch])
    assert any([os.path.exists(os.path.join(parent, netcon, a, '.libs')) for a in arch])

except AssertionError:
    logger.warning("Neuron mechanisms are not compiled.")
    logger.warning("Trying to compile them. Only works, if nrnivmodl is in PATH")
    os.system(
        '(cd {path}; nrnivmodl)'.format(path=os.path.join(parent, channels)))
    os.system(
        '(cd {path}; nrnivmodl)'.format(path=os.path.join(parent, netcon)))

    try:
        assert any(
            [os.path.exists(os.path.join(parent, channels, a)) for a in arch])
        assert any(
            [os.path.exists(os.path.join(parent, netcon, a)) for a in arch])
    except AssertionError:
        logger.warning("Could not compile mechanisms. Please do it manually")
        raise

logger.info("Loading mechanisms:")

try:
    with stream_to_logger(logger=logger):
        mechanisms_loaded = neuron.load_mechanisms(os.path.join(parent, channels))
        netcon_loaded = neuron.load_mechanisms(os.path.join(parent, netcon))
    assert mechanisms_loaded, "Couldn't load mechanisms."
    assert netcon_loaded, "Couldn't load netcon"
except Exception as e:
     raise e