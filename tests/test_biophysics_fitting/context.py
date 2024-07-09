from __future__ import absolute_import
import os
import sys

PARENT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

sys.path.insert(0, PARENT)