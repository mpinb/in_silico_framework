"""
This directory contains the `.mod` files that define the biophysical behaviour of ion channels, such as conductivity, states, derivative states and initial conditions. 
In addition, it contains network connectivity parameters that define synaptic connections.

These are used by the NEURON simulator as variable parameters for solving the partial differential equations that describe the biophysics of a neuron.

In this direrctory, you will find cell-specific biphysical mechanisms organizeed per folder. Each folder has its own __init__ file that sets up these mechanisms using NEURON.
"""

from . import l5pt