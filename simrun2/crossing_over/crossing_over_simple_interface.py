import tempfile
import shutil
import dask
from .utils import filter_by_time, merge_synapse_activation
from ..generate_synapse_activations import generate_synapse_activations
from ..run_existing_synapse_activations import run_existing_synapse_activations
import os
import pandas as pd
from model_data_base.IO.roberts_formats import write_pandas_synapse_activation_to_roberts_format
from model_data_base.IO.roberts_formats import read_pandas_synapse_activation_from_roberts_format
import neuron

h = neuron.h
# from compatibility import synchronous_scheduler


def scale_apical(cell):
    '''
    scale apical diameters depending on
    distance to soma; therefore only possible
    after creating complete cell
    '''
    dendScale = 2.5
    scaleCount = 0
    for sec in cell.sections:
        if sec.label == 'ApicalDendrite':
            dist = cell.distance_to_soma(sec, 1.0)
            if dist > 1000.0:
                continue
#            for cell 86:
            if scaleCount > 32:
                break
            scaleCount += 1
            #            dummy = h.pt3dclear(sec=sec)
            for i in range(sec.nrOfPts):
                oldDiam = sec.diamList[i]
                newDiam = dendScale * oldDiam
                h.pt3dchange(i, newDiam, sec=sec)


#                x, y, z = sec.pts[i]
#                sec.diamList[i] = sec.diamList[i]*dendScale
#                d = sec.diamList[i]
#                dummy = h.pt3dadd(x, y, z, d, sec=sec)


def crossing_over_helper(pdf,
                         time,
                         cellParamName,
                         evokedUpParamName,
                         dirPrefix='',
                         nSweeps=1000,
                         tStop=345,
                         silent=True,
                         scale_apical=scale_apical):
    synfile_temppath = tempfile.mkdtemp(dir=dirPrefix,
                                        prefix='new_synapse_activation')
    delayed = generate_synapse_activations(cellParamName,
                                           evokedUpParamName,
                                           dirPrefix=synfile_temppath,
                                           nSweeps=nSweeps,
                                           nprocs=1,
                                           silent=silent)
    synfiles = delayed.compute(get=dask.get)[0]

    pdf = filter_by_time(pdf, lambda x: x <= time)
    merged_synfile_temppath = tempfile.mkdtemp(
        dir=dirPrefix, prefix='merged_synapse_activation')
    merged_synfile_paths = []
    for synfilename in synfiles[0]:
        synfile = read_pandas_synapse_activation_from_roberts_format(
            synfilename)
        synfile = filter_by_time(synfile, lambda x: x > time)
        synfile = merge_synapse_activation(pdf, synfile)
        merged_synfile_paths.append(
            os.path.join(merged_synfile_temppath,
                         os.path.basename(synfilename)))
        write_pandas_synapse_activation_to_roberts_format(
            merged_synfile_paths[-1], synfile)
    delayed = run_existing_synapse_activations(cellParamName,
                                               evokedUpParamName,
                                               merged_synfile_paths,
                                               dirPrefix=dirPrefix,
                                               nprocs=1,
                                               tStop=tStop,
                                               silent=silent,
                                               scale_apical=scale_apical)
    ret = delayed.compute(get=dask.get)
    shutil.rmtree(synfile_temppath)
    shutil.rmtree(merged_synfile_temppath)
    return ret


delayed_crossing_over_helper = dask.delayed(crossing_over_helper)


def crossing_over(mdb,
                  sim_trails,
                  time,
                  cellParamName,
                  evokedUpParamName,
                  dirPrefix='',
                  nSweeps=1000,
                  tStop=345,
                  silent=True,
                  scale_apical=scale_apical):
    if isinstance(sim_trails, str):
        sim_trails = [sim_trails]
    dirPrefixes = []
    delayeds = []
    synapse_activation = mdb['synapse_activation']
    for sim_trail in sim_trails:
        sa = synapse_activation.loc[sim_trail]
        sim_trail = sim_trail.replace('/', '__')
        path = os.path.join(dirPrefix, sim_trail)
        if not os.path.exists(path):
            os.makedirs(path)
        #print path
        dirPrefixes.append(path)
        delayeds.append(
            delayed_crossing_over_helper(sa,
                                         time,
                                         cellParamName,
                                         evokedUpParamName,
                                         dirPrefix=path,
                                         nSweeps=nSweeps,
                                         tStop=tStop,
                                         silent=silent,
                                         scale_apical=scale_apical))
    pdf = pd.DataFrame(
        dict(sim_trail_index=sim_trails, simResultDirPrefixes=dirPrefixes))
    pdf.to_csv(os.path.join(dirPrefix, 'sim_trail_path_mapping.csv'),
               index=False)
    return pdf, dask.delayed(delayeds)