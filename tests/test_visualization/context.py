from __future__ import absolute_import
import os
import sys

parent = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
this_folder = os.path.abspath(os.path.dirname(__file__))

sys.path.insert(0, parent)
