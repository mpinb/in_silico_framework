from __future__ import absolute_import
from ._matplotlib_import import *
import sys
import time
import os, os.path
import glob
#for some reason, the neuron import works on the florida servers only works if tables was imported first
import tables
import neuron
import single_cell_parser as scp
import single_cell_parser.analyze as sca
import numpy as np

h = neuron.h
import dask
from .seed_manager import get_seed
from .utils import *

def parameters_to_cell(neuronParam, networkParam, synfile = None,\
                     dirPrefix = '', tStop = 345.0, scale_apical = scale_apical, \
                     range_vars = None, allPoints=False, \
                     cell = None, evokedNW = None):

    neuronParam = load_param_file_if_path_is_provided(neuronParam)
    networkParam = load_param_file_if_path_is_provided(networkParam)

    if cell is None:
        cell = scp.create_cell(neuronParam.neuron,
                               scaleFunc=scale_apical,
                               allPoints=allPoints)

    neuronParam.sim.tStop = tStop
    dt = neuronParam.sim.dt

    if evokedNW is None:
        evokedNW = scp.NetworkMapper(cell, networkParam.network,
                                     neuronParam.sim)
    if synfile is None:
        evokedNW.create_saved_network2()
    else:
        evokedNW.reconnect_saved_synapses(synfile)

    if range_vars is not None:
        if isinstance(range_vars, str):
            range_vars = [range_vars]
        for var in range_vars:
            cell.record_range_var(var)

    tVec = h.Vector()
    tVec.record(h._ref_t)
    cell.t = tVec
    scp.init_neuron_run(neuronParam.sim,
                        vardt=False)  #trigger the actual simulation
    return cell, evokedNW