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

'''Convert a :py:class:`~single_cell_parser.cell.Cell` object to a serializable object and vice versa.
'''
from __future__ import absolute_import
import numpy as np
import pandas as pd
from data_base.utils import silence_stdout
from data_base.dbopen import dbopen
from .cell_parser import CellParser
from . import ParameterSet

__author__  = 'Arco Bast'
__date__    = '2016/2017'

def convert_hoc_array_to_np_array(hoc_array):
    '''Convert hoc array to list of lists
    
    Args:
        hoc_array: hoc array
        
    Returns:
        list: list of lists
    '''
    return [np.array(x) for x in hoc_array]


def convert_dict_of_hoc_arrays_to_dict_of_np_arrays(hoc_array_dict):
    '''Convert dictionary of hoc arrays to dictionary of list of lists'''
    out = {}
    for name in hoc_array_dict:
        out[name] = convert_hoc_array_to_np_array(hoc_array_dict[name])
    return out


def cell_to_serializable_object(cell):
    '''Convert a :py:class:`~single_cell_parser.cell.Cell` object to a dict, so that it can be serialized.

    Useful for parallellization using e.g. Dask or Joblib.
    
    The serialized object contains the following information:
    
    - tVec: time vector
    - parameters: dictionary of parameters
    - allPoints: point coordinates fo the cell
    - sections: list of dictionaries containing the following information for each section:
        - recVList: membrane potential
        - recordVars: dictionary of hoc arrays
        - label: label of the section
        - sec_id: ID of the section
        - parent_id: ID of the parent section
    - synapses: dictionary of synapse populations, each containing a list of synapses with the following information:
        - preCell: dictionary containing the spike times of the presynaptic cell
        - coordinates: coordinates of the synapse
    - hoc: hoc file content

    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): cell object

    Returns:
        dict: serializable cell object
    '''
    out = {}
    out['sections'] = []
    out['tVec'] = np.array(cell.tVec)
    out['parameters'] = cell.parameters
    # out['allPoints'] = cell.allPoints
    for lv, sec in enumerate(cell.sections):
        dummy = {}
        dummy['recVList'] = convert_hoc_array_to_np_array(sec.recVList)
        dummy['recordVars'] = convert_dict_of_hoc_arrays_to_dict_of_np_arrays(
            sec.recordVars)
        dummy['label'] = sec.label
        dummy['sec_id'] = lv
        dummy['parent_id'] = [
            lv_ for lv_, s in enumerate(cell.sections) if s == sec.parent
        ][0] if sec.parent is not None else None
        out['sections'].append(dummy)

    out['synapses'] = {}
    # TODO: THe Synapse class can likely be parallellized (see scp.synapse)
    # But do we need all the information?
    for population in cell.synapses.keys():
        dummy_population = []  # synapses that belong to this population
        for synapse in cell.synapses[population]:
            dummy_synapse = {}
            dummy_synapse["preCell"] = {
                "spikeTimes": synapse.preCell.spikeTimes
            }
            dummy_synapse["coordinates"] = synapse.coordinates
            # TODO other synapse attributes
            dummy_population.append(dummy_synapse)
        out['synapses'][population] = dummy_population

    with dbopen(cell.hoc_path) as f:
        out['hoc'] = f.read()
    return out


from data_base.utils import mkdtemp
import os


def restore_cell_from_serializable_object(sc):
    """Restore a :py:class:`~single_cell_parser.cell.Cell` object from a serializable object.
    
    Args:
        sc (dict): serializable object
        
    Returns:
        :py:class:`~single_cell_parser.cell.Cell`: cell object
    """
    # create hoc file
    with mkdtemp() as tempdir:
        hoc_file_path = os.path.join(tempdir, 'morphology.hoc')
        with dbopen(hoc_file_path, 'w') as hoc_file:
            hoc_file.write(sc['hoc'])

        ##############################
        # the following code has to be kept up to date with the
        # single_cell_parser.create_cell method
        ##############################

        axon = False
        if 'AIS' in set([sec['label'] for sec in sc['sections']]):
            axon = True

        parser = CellParser(hoc_file_path)
        with silence_stdout:
            # we do not scale! maybe trigger a warning?
            # or better deprecate the scale apical function?
            parser.spatialgraph_to_cell(
                ParameterSet(sc['parameters']),
                axon,
                scaleFunc=None
                )

            # the following is needed to assure that the reconstructed cell
            # has an equal amount of segments compared to the original cell
            parser.set_up_biophysics(
                ParameterSet(sc['parameters']),
                full = sc.get('allPoints', False)
                )

        ##############################
        # end of code from single_cell_parser.create_cell
        ##############################

    cell = parser.cell
    cell.tVec = sc['tVec']
    for outdict, sec in zip(sc['sections'], cell.sections):
        for name in outdict:
            setattr(sec, name, outdict[name])
    return cell


def save_cell_to_file(path, cell):
    """Save a :py:class:`~single_cell_parser.cell.Cell` object to a file in .pickle format.
    
    Args:
        path (str): path to file
        cell (:py:class:`~single_cell_parser.cell.Cell`): cell object
        
    Returns:
        None. Writes out the cell object to :paramref:`path` in .pickle format.
    """
    sc = cell_to_serializable_object(cell)
    pd.Series([sc]).to_pickle(path)


def load_cell_from_file(path):
    """Load a :py:class:`~single_cell_parser.cell.Cell` object from a file in .pickle format.
    
    Args:
        path (str): path to .pickle file
        
    Returns:
        :py:class:`~single_cell_parser.cell.Cell`: cell object
    """
    pds = pd.read_pickle(path)
    sc = pds[0]
    return restore_cell_from_serializable_object(sc)
