'''
Created 2016/2017

@author: arco
'''
from __future__ import absolute_import
import numpy as np
import pandas as pd
from six import BytesIO
import sumatra
from data_base.utils import silence_stdout
from data_base.dbopen import dbopen
from .cell_parser import CellParser


def convert_hoc_array_to_np_array(hoc_array):
    '''converts hoc array to list of lists'''
    return [np.array(x) for x in hoc_array]


def convert_dict_of_hoc_arrays_to_dict_of_np_arrays(hoc_array_dict):
    '''converts dictionary of hoc arrays to dictionary of list of lists'''
    out = {}
    for name in hoc_array_dict:
        out[name] = convert_hoc_array_to_np_array(hoc_array_dict[name])
    return out


def cell_to_serializable_object(cell):
    '''takes cell object and returns an object, that contains the saved information
    (recorded range vars, voltage) and that can be serialized.'''
    out = {}
    out['sections'] = []
    out['tVec'] = np.array(cell.tVec)
    out['parameters'] = cell.parameters
    out['allPoints'] = cell.allPoints
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
            parser.spatialgraph_to_cell(sumatra.parameters.NTParameterSet(
                sc['parameters']),
                                        axon,
                                        scaleFunc=None)

            # the following is needed to assure that the reconstructed cell
            # has an equal amount of segments compared to the original cell
            parser.set_up_biophysics(
                sumatra.parameters.NTParameterSet(sc['parameters']),
                sc['allPoints'])

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
    sc = cell_to_serializable_object(cell)
    pd.Series([sc]).to_pickle(path)


def load_cell_from_file(path):
    pds = pd.read_pickle(path)
    sc = pds[0]
    return restore_cell_from_serializable_object(sc)