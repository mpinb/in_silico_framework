import os, platform

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
        [os.path.exists(os.path.join(parent, channels, a)) for a in arch])
    assert any([os.path.exists(os.path.join(parent, netcon, a)) for a in arch])
except AssertionError:
    print("neuron mechanisms are not compiled.")
    print("Trying to compile them. Only works, if nrnivmodl is in PATH")
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
        print("Could not complile mechanisms. Please do it manually")
        raise

print("Loading mechanisms:")
neuron.load_mechanisms(os.path.join(parent, channels))
neuron.load_mechanisms(os.path.join(parent, netcon))
