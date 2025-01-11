"""Run simulations of network-embedded neuron models.

This package provides a framework to run simulations of network-embedded neuron models.
They allow to run new simulations from existing parameter files, or to re-run existing simulations with
adapted parameters for the cell and/or network.
"""
import tables
import neuron
from mechanisms import l5pt as l5pt_mechanisms
#neuron.load_mechanisms('/nas1/Data_arco/project_src/mechanisms/netcon')
#neuron.load_mechanisms('/nas1/Data_arco/project_src/mechanisms/channels')

from compatibility import init_simrun_compatibility
init_simrun_compatibility()