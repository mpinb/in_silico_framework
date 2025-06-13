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

'''Compute synapse distances and activation times.

This module provides functions to compute the distances of synapses to the soma 
and to save the activation times and soma distances of synapses to a ``.csv`` file.

See also:
    The :ref:`syn_activation_format` file format.
'''

import numpy as np
import single_cell_parser as scp
from data_base.dbopen import dbopen

__author__ = "Robert Egger"
__date__ = "2012-04-02"


def compute_synapse_distances_times(fname, cell, t=None, synTypes=None):
    """Save a :py:class:`single_cell_parser.cell.Cell` object's synapse distances and activation times to a ``.csv`` file.
    
    The following information is saved:
    
    - synapse type: to which presynaptic cell type this synapse belongs to.
    - synapse ID: unique identifier for the synapse.
    - soma distance: distance from the synapse to the soma.
    - section ID: ID of the section of the postsynaptic cell that contains this synapse.
    - section pt ID: ID of the point in the section that contains this synapse.
    - dendrite label: label of the dendrite that contains this synapse.
    - activation times: times at which the synapse was active (ms).
        
    Args:
        fname (str): The output file name as a ful path, including the file extension. Preferably unique (see e.g. :py:meth:`~simrun.generate_synapse_activations._evoked_activity` for the generation of unique syapse activation filenames)
        cell (:py:class:`single_cell_parser.cell.Cell`): Cell object
        synTypes (list): list of synapse types. Default: the keys of the `cell.synapses` dictionary
        
    Returns:
        None. Writes out the synapse .csv file to :paramref:`fname`.

    See also:
        The :ref:`syn_activation_format` file format.
    """
    synDistances = {}
    synTimes = {}
    activeSyns = {}
    synCnt = 0
    if synTypes is None:
        synTypes = list(cell.synapses.keys())
        synTypes.sort
    for synType in synTypes:
        synDistances[synType] = compute_syn_distances(cell, synType)
        synTimes[synType] = []
        activeSyns[synType] = []
        for syn in cell.synapses[synType]:
            if not syn.is_active():
                activeSyns[synType].append(False)
                synTimes[synType].append([])
            else:
                activeSyns[synType].append(True)
                tmpSynTimes = syn.releaseSite.spikeTimes[:]
                synTimes[synType].append(tmpSynTimes)
            synCnt += 1

    scp.write_synapse_activation_file(
        fname, cell, synTypes, synDistances, synTimes, activeSyns
        )


def synapse_activation_times(tVec, cntVec):
    """Parse the spike times from a list of spike counts and corresponding time points.
    
    Args:
        tVec (neuron.h.Vector | array): list of time points
        cntVec (neuron.h.Vector | array): list of cummulative spike counts

    Returns:
        list: list of spike times

    Example:
        >>> tVec = [0, 1, 2, 3, 4, 5]
        >>> cntVec = [0, 0, 0, 1, 1, 2]
        >>> synapse_activation_times(tVec, cntVec)
        [3, 5]
    """
    synTVec = []
    for i in range(1, len(cntVec)):
        if cntVec[i] > cntVec[i - 1]:
            synTVec.append(tVec[i])
    return synTVec


def synapse_distances(pname):
    """Compute the distances of synapses to the soma from a network parameter file.

    .. deprecated:: 0.1.0
       Network parameter files no longer have the keys ``post`` and ``pre`` under the ``network`` key.
       Instead, specific celltypes are given (see: :ref:`network_parameters_format`),
       and the postsynaptic cell has its own parameter file (see: :ref:`cell_parameters_format`).

    Args:
        pname (str): path to the network parameter file

    Returns:
        None. Writes out the synapse distances to a file.

    :skip-doc:
    """
    parameters = scp.build_parameters(pname)
    cellParam = parameters.network.post
    preParam = parameters.network.pre

    parser = scp.CellParser(cellParam.filename)
    parser.spatialgraph_to_cell()
    cell = parser.cell
    for preType in list(preParam.keys()):
        synapseFName = preParam[preType].synapses.realization
        synDist = scp.read_synapse_realization(synapseFName)
        mapper = scp.SynapseMapper(cell, synDist)
        mapper.map_synapse_realization()

    for synType in list(cell.synapses.keys()):
        dist = compute_syn_distances(cell, synType)
        name = parameters.info.outputname
        name += '_'
        name += synType
        name += '_syn_distances.csv'
        with dbopen(name, 'w') as distFile:
            header = 'Distance to soma (micron)\n'
            distFile.write(header)
            for d in dist:
                distFile.write(str(d) + '\n')


def synapse_distances_2D(pname):
    """Compute the 2D-projected distances of synapses to the soma from a network parameter file.
    
    .. deprecated:: 0.1.0
       Network parameter files no longer have the keys ``post`` and ``pre`` under the ``network`` key.
       Instead, specific celltypes are given (see: :ref:`network_parameters_format`),
       and the postsynaptic cell has its own parameter file (see: :ref:`cell_parameters_format`).

    Args:
        pname (str): path to the network parameter file
    
    Returns:
        None. Writes out the synapse distances to a file.

    :skip-doc:
    """
    parameters = scp.build_parameters(pname)
    cellParam = parameters.network.post
    preParam = parameters.network.pre

    parser = scp.CellParser(cellParam.filename)
    parser.spatialgraph_to_cell()
    cell = parser.cell
    for preType in list(preParam.keys()):
        synapseFName = preParam[preType].synapses.realization
        synDist = scp.read_synapse_realization(synapseFName)
        mapper = scp.SynapseMapper(cell, synDist)
        mapper.map_synapse_realization()

    for synType in list(cell.synapses.keys()):
        dist = compute_syn_distances_2Dprojected(cell, synType)
        name = parameters.info.outputname
        name += '_'
        name += synType
        name += '_syn_distances_2Dprojected.csv'
        with dbopen(name, 'w') as distFile:
            header = 'Distance to soma (micron)\n'
            distFile.write(header)
            for d in dist:
                distFile.write(str(d) + '\n')


# def compute_syn_distances(cell, synType, label=None):
#     '''
#     computes distances of all synapses on dendrite w.r.t. soma

#     cell is cell object with attached synapses
#     presynaptic cell type given by synType (string)
#     optional: dendrite type given by label (string)

#     returns 1D numpy array of distances to soma
#     '''
#     if not cell.synapses.has_key(synType):
#         errStr = 'Cell does not have synapses of type %s' % synType
#         raise KeyError(errStr)

#     distances = []
#     for syn in cell.synapses[synType]:
#         currentSec = cell.sections[syn.secID]
#         if label is not None and currentSec.label != label:
#             continue

#         if currentSec.label == 'Soma':
#             dist = 0.0
#             distances.append(dist)
#             continue

#         parentSec = currentSec.parent
#         '''compute distance from synapse location to parent branch first'''
#         dist = 0.0
#         dist = syn.x*currentSec.L
#         parentLabel = parentSec.label
#         while parentLabel != 'Soma':
#             dist += parentSec.L
#             currentSec = parentSec
#             parentSec = currentSec.parent
#             parentLabel = parentSec.label
#         distances.append(dist)

#     return np.array(distances)


def compute_syn_distances_2Dprojected(cell, synType, label=None):
    '''Computes the XY-projected distances (to soma) of all synapses on dendrite.
    
    Used for computing synapse distances projected on a 2D plane (the XY-plane),
    as seen during 2-photon spine imaging.

    Args: 
        cell (:py:class:`single_cell_parser.cell.Cell`): cell object with attached synapses.
        synType (str): presynaptic cell type.
        label (str, optional): dendrite type (e.g. "ApicalDendrite") to compute distances for.
    
    Returns:
        numpy.ndarray: 1D array of 2D- proejcted distances to soma
    '''
    if synType not in cell.synapses:
        errStr = 'Cell does not have synapses of type %s' % synType
        raise KeyError(errStr)

    somaLoc = cell.soma.pts[cell.soma.nrOfPts // 2]
    distances = []
    for syn in cell.synapses[synType]:
        currentSec = cell.sections[syn.secID]
        if label is not None and currentSec.label != label:
            continue
        synLoc = syn.coordinates
        diff = synLoc - somaLoc
        dist = np.sqrt(np.dot(diff[:2], diff[:2]))
        distances.append(dist)
    return np.array(distances)


def get_dist(x1, x2):
    """Compute the Euclidean distance between two points.
    
    Args:
        x1 (list): first point
        x2 (list): second point
        
    Returns:
        float: Euclidean distance between the two points
    """
    assert len(x1) == len(x2)
    return np.sqrt(sum((xx1 - xx2)**2 for xx1, xx2 in zip(x1, x2)))


def compute_distance_to_soma(sec, x, cell=None, consider_gap_to_soma=False):
    '''Computes the distance from a point to the soma.

    The point for which to compute the distance is defined by a section
    and a relative point on that section (the x coordinate between 0 and 1).

    Used in :py:meth:`compute_syn_distance` and :py:meth:`compute_syn_distances`.

    Args:
        sec (:py:class:`single_cell_parser.cell.PySection` | int): 
            Section or section ID of the cell.
            If the section ID is given, :paramref:`cell` must be provided.
        x (float): 
            Relative point on section, from 0 to 1.
        cell (:py:class:`single_cell_parser.cell.Cell`, optional): 
            Only required if :paramref:`sec` is the section ID.
        consider_gap_to_soma (bool, optional): 
            Accounts for the fact that dendrites don't actually touch the soma, and adds the
            distance between the last point of the parent section and the first point of the
            current section to the distance.
            Default: False

    Returns:
        float: distance to the soma
    '''

    if isinstance(sec, int) and cell is not None:
        sec = cell.sections[sec]
    elif isinstance(sec, int) and cell is None:
        errStr = 'If sec is specified as an integer, a cell object must be given. Otherwise, specify sec as a PySection object.'
        raise ValueError(errStr)
    currentSec = sec
    if currentSec.label == 'Soma':
        dist = 0.0
    else:
        parentSec = currentSec.parent

        dist = 0.0
        dist = x * currentSec.L
        parentLabel = parentSec.label
        while parentLabel != 'Soma':
            dist += parentSec.L * currentSec.parentx
            currentSec = parentSec
            parentSec = currentSec.parent
            parentLabel = parentSec.label
        if consider_gap_to_soma:
            dist += get_dist(currentSec.pts[0], parentSec.pts[-1])
    return dist


def compute_syn_distance(
    cell,
    syn,
    consider_gap_to_soma=False
    ):
    """Computes the distance from a single synapse to the soma.

    Used in :py:meth:`compute_syn_distances`.
    
    Args:
        cell (:py:class:`single_cell_parser.cell.Cell`): cell object with attached synapses.
        syn (:py:class:`single_cell_parser.synapse.Synapse`): synapse object.
        consider_gap_to_soma (bool, optional): 
            Account for the fact that dendrites don't actually touch the soma, and add the 
            distance between the last point of the parent section and the first point of the 
            current section to the distance.
            Default: False
    """
    ## same as Robert's method but can get one synapse at a time
    currentSec = cell.sections[syn.secID]
    x = syn.x
    return compute_distance_to_soma(
        currentSec,
        x,
        consider_gap_to_soma=consider_gap_to_soma)


def compute_syn_distances(
    cell,
    synType,
    label=None,
    consider_gap_to_soma=False):  
    '''Computes distances (to soma) of all synapses on the dendrite.
    
    Args:
        cell (:py:class:`single_cell_parser.cell.Cell`): cell object with attached synapses.
        synType (str): presynaptic cell type to compute distances for.
        label (str, optional): 
            dendrite type (e.g. "ApicalDendrite") to compute distances for.
            Default: None (all dendrites)
    
    Returns:
        numpy.ndarray: 1D array of distances to soma

    Raises:
        KeyError: if the cell does not have synapses of type :paramref:`synType`.
    '''
    ## updated to use new method for getting somadistance of one synapse at a time
    if synType not in cell.synapses:
        errStr = 'Cell does not have synapses of type %s' % synType
        raise KeyError(errStr)
    distances = []
    for syn in cell.synapses[synType]:
        currentSec = cell.sections[syn.secID]
        if label is not None and currentSec.label != label:
            continue

        if currentSec.label == 'Soma':
            dist = 0.0
            distances.append(dist)
            continue

        distances.append(compute_syn_distance(cell, syn, consider_gap_to_soma))
    return np.array(distances)
