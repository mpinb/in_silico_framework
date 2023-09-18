from model_data_base.mdbopen import resolve_mdb_path
import logging
log = logging.getLogger(__name__)

def load_param_file_if_path_is_provided(pathOrParam):
    import single_cell_parser as scp
    if isinstance(pathOrParam, str):
        pathOrParam = resolve_mdb_path(pathOrParam)
        return scp.build_parameters(pathOrParam)
    elif isinstance(pathOrParam, dict):
        return scp.NTParameterSet(pathOrParam)
    else:
        return pathOrParam
    
def scale_apical(cell):
    '''
    scale apical diameters depending on
    distance to soma; therefore only possible
    after creating complete cell
    '''
    import neuron
    h = neuron.h
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
                newDiam = dendScale*oldDiam
                h.pt3dchange(i, newDiam, sec=sec)
#                x, y, z = sec.pts[i]
#                sec.diamList[i] = sec.diamList[i]*dendScale
#                d = sec.diamList[i]
#                dummy = h.pt3dadd(x, y, z, d, sec=sec)
    
    log.info('Scaled {:d} apical sections...'.format(scaleCount))
    
class defaultValues:
    name = 'C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center'
    cellParamName = '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/L5tt/network_embedding/postsynaptic_location/3x3_C2_sampling/C2center/86_CDK_20041214_BAC_run5_soma_Hay2013_C2center_apic_rec.param'
    networkName = 'C2_evoked_UpState_INH_PW_1.0_SuW_0.5_active_ex_timing_C2center.param'
    
import tarfile
import os
import shutil
def tar_folder(source_dir, delete_folder = True):
    parent_folder = os.path.dirname(source_dir)
    folder_name = os.path.basename(source_dir)
    source_dir = source_dir.rstrip('/')
    tar_path = source_dir + '.tar.running'
    command = 'tar -cf {} -C {} .'.format(tar_path, source_dir)
    if os.system(command):
        raise RuntimeError('{} failed!'.format(str(command)))
    if delete_folder:
        if os.system('rm -r {}'.format(source_dir)):
            raise RuntimeError('deleting folder {} failed!'.format(str(source_dir)))
    os.rename(source_dir + '.tar.running', source_dir + '.tar')
            
def chunkIt(seq, num):
    '''splits seq in num lists, which have approximately equal size.
    https://stackoverflow.com/questions/2130016/splitting-a-list-of-arbitrary-size-into-only-roughly-n-equal-parts
    '''
    avg = len(seq) / float(num)
    out = []
    last = 0.0
    
    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg
    
    return [o for o in out if o] #filter out empty lists

import sys
import os

def silence_stdout(fun):
    '''robustly silences a function and restores stdout afterwars'''
    def silent_fun(*args, **kwargs):
        stdout_bak = sys.stdout
        sys.stdout = open(os.devnull, "w")
        try:
            res = fun(*args, **kwargs)
        except:
            raise
        finally:
            sys.stdout = stdout_bak
        return res
    return silent_fun

       