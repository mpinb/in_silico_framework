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

import numpy as np
from data_base.utils import silence_stdout
import single_cell_parser as scp
import single_cell_parser.analyze as sca
import logging
logger = logging.getLogger("ISF").getChild(__name__)
from config.cell_types import EXCITATORY, INHIBITORY
# import Interface as I # moved to bottom becose auf circular import


def get_cell_activations(network_param, tStop=350):
    param = network_param
    out_dict = {}
    for celltype in list(param['network'].keys()):
        out = [0.] * tStop
        if isinstance(param['network'][celltype]['celltype'], str):
            out = np.array(out) + 1 / param['network'][celltype]['interval']
        else:
            dummy = param['network'][celltype]['celltype']
            for x, y in zip(dummy['pointcell']['intervals'],
                            dummy['pointcell']['probabilities']):
                l = int(np.round(x[1] - x[0]))
                for lv in range(l):
                    out[int(dummy['pointcell']['offset'] + x[0]) +
                        lv] = float(y) / l
            out = np.array(out)
            out += 1 / dummy['spiketrain']['interval']
        out = out * param['network'][celltype]['synapses']['releaseProb']
        out_dict[celltype] = out
    return out_dict


def get_number_of_synapses_closer_than_x(distance, network_param, cell_param):
    cell = scp.create_cell(cell_param.neuron)
    cell_param.sim.tStop = 1
    evokedNW = scp.NetworkMapper(cell, network_param.network, cell_param.sim)
    evokedNW.create_saved_network2()
    out = {}
    for type_ in list(cell.synapses.keys()):
        out[type_] = len([
            x for x in sca.compute_syn_distances(cell, type_) if x <= distance
        ])
    return out


get_number_of_synapses_closer_than_x = silence_stdout(
    get_number_of_synapses_closer_than_x)


def get_expectancy_value_of_activated_prox_synapses_by_celltype(
        cell_param,
        network_param,
        seed=None,
        tStop=345,
        proximal=None,
        distal=None):
    if proximal is not None:
        raise NotImplementedError()
    int(distal)
    synapse_numbers = get_number_of_synapses_closer_than_x(
        distal, network_param, cell_param)
    cell_activations = get_cell_activations(network_param, tStop=tStop)
    assert set(synapse_numbers.keys()) == set(cell_activations.keys())
    return {
        key: cell_activations[key] * float(synapse_numbers[key])
        for key in list(synapse_numbers.keys())
    }


def get_expectancy_value_of_activated_prox_synapses_by_EI(
        cell_param,
        network_param,
        seed=None,
        tStop=345,
        proximal=None,
        distal=None):
    dict_ = get_expectancy_value_of_activated_prox_synapses_by_celltype(
        cell_param,
        network_param,
        seed=seed,
        tStop=tStop,
        proximal=proximal,
        distal=distal)
    EXC = sum([
        dict_[key]
        for key in list(dict_.keys())
        if key.split('_')[0] in EXCITATORY
    ])
    INH = sum([
        dict_[key]
        for key in list(dict_.keys())
        if key.split('_')[0] in INHIBITORY
    ])
    return EXC, INH


def get_poisson_realizations_from_expectancy_values(
    expectancy_values,
    nSweeps=1000):
    dummy = np.vstack(
        [np.random.poisson(lam=x, size=nSweeps) for x in expectancy_values])
    return np.transpose(dummy)
