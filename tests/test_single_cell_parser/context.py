from __future__ import absolute_import
import os
import sys
import tempfile
import getting_started
import neuron
h = neuron.h

parent = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
this_folder = os.path.abspath(os.path.dirname(__file__))
fname = os.path.join(this_folder, 'data', '85.hoc')
sys.path.insert(0, parent)
