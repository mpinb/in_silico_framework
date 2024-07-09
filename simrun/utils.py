from data_base.dbopen import resolve_db_path
import pandas as pd
import single_cell_parser as scp
import os, sys, tarfile, shutil
import logging
import single_cell_parser as scp
import pandas as pd
import os
import single_cell_parser as scp
import inspect
import six
from collections import defaultdict
defaultdict_defaultdict = lambda: defaultdict(lambda: defaultdict_defaultdict())

def get_cellnumbers_from_confile(confile):
    con = scp.reader.read_functional_realization_map(confile)
    con = con[0]
    return {k: con[k][-1][1] + 1 for k in list(con.keys())}


def split_network_param_in_one_elem_dicts(dict_):
    out = []
    for k in list(dict_['network'].keys()):
        d = defaultdict_defaultdict()
        d['network'][k] = dict_['network'][k]
        out.append(scp.NTParameterSet(d))
    return out


def get_default_arguments(func):
    '''Gets the keyword arguments with their default value from any function.
    
    import six
    Returns: dictionary, function names are keys, default values are values'''
    o = inspect.getargspec(func)
    names = o.args[-len(six.get_function_defaults(func)):]
    defaults = o.defaults
    return {n: d for n, d in zip(names, defaults) if d is not None}


def set_default_arguments_if_not_set(o, kwargs):
    '''Used to update attributes of an object based on a dictionary.
    If the attribute is already set, it is NOT opverwritten.
    
    Usecase: If an object has been pickled and the keyword arguments have been extended post hoc, 
    the new keyword arguments are missing. This can be used to update the object accordingly.
    
    import six
    Returns: None'''
    for n, v in six.iteritems(kwargs):
        try:
            getattr(o, n)
        except AttributeError:
            errstr = 'Warning! Setting {} to default value {}'
            print(errstr.format(n, v))
            setattr(o, n, v)

def get_fraction_of_landmarkAscii(frac, path):
    'returns fraction of landmarkAscii files defined in path'
    f = os.path.basename(path)
    celltype = f.split('.')[-2]
    positions = scp.read_landmark_file(path)
    pdf = pd.DataFrame({'positions': positions, 'label': celltype})
    if len(pdf) == 0:  # cannot sample from empty pdf
        return pdf
    if frac >= 1:
        return pdf
    else:
        return pdf.sample(frac=frac)


def get_fraction_of_landmarkAscii_dir(frac, basedir=None):
    'loads all landmarkAscii files in directory and returns dataframe containing'\
    'position and filename (without suffix i.e. without .landmarkAscii)'
    out = []
    for f in os.listdir(basedir):
        if not f.endswith('landmarkAscii'):
            continue
        out.append(get_fraction_of_landmarkAscii(1, os.path.join(basedir, f)))

    return pd.concat(out).sample(frac=frac).sort_values('label').reset_index(
        drop=True)

def select_cells_that_spike_in_interval(
    sa,
    tmin,
    tmax,
    set_index=[
        'synapse_ID', 'synapse_type'
    ]):
    pdf = sa.set_index(list(set_index))
    pdf = pdf[[c for c in pdf.columns if c.isdigit()]]
    pdf = pdf[((pdf >= tmin) & (pdf < tmax)).any(axis=1)]
    cells_that_spike = pdf.index
    cells_that_spike = cells_that_spike.tolist()
    return cells_that_spike

logger = logging.getLogger("ISF").getChild(__name__)


def load_param_file_if_path_is_provided(pathOrParam):
    import single_cell_parser as scp
    if isinstance(pathOrParam, str):
        pathOrParam = resolve_db_path(pathOrParam)
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
            # for cell 86:
            if scaleCount > 32:
                break
            scaleCount += 1
            # dummy = h.pt3dclear(sec=sec)
            for i in range(sec.nrOfPts):
                oldDiam = sec.diamList[i]
                newDiam = dendScale * oldDiam
                h.pt3dchange(i, newDiam, sec=sec)
                # x, y, z = sec.pts[i]
                # sec.diamList[i] = sec.diamList[i]*dendScale
                # d = sec.diamList[i]
                # dummy = h.pt3dadd(x, y, z, d, sec=sec)

    logger.info('Scaled {:d} apical sections...'.format(scaleCount))


class defaultValues:
    name = 'C2_evoked_UpState_INH_PW_1.0_SuW_0.5_C2center'
    cellParamName = '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/L5tt/network_embedding/postsynaptic_location/3x3_C2_sampling/C2center/86_CDK_20041214_BAC_run5_soma_Hay2013_C2center_apic_rec.param'
    networkName = 'C2_evoked_UpState_INH_PW_1.0_SuW_0.5_active_ex_timing_C2center.param'


def tar_folder(source_dir, delete_folder=True):
    parent_folder = os.path.dirname(source_dir)
    folder_name = os.path.basename(source_dir)
    source_dir = source_dir.rstrip('/')
    tar_path = source_dir + '.tar.running'
    command = 'tar -cf {} -C {} .'.format(tar_path, source_dir)
    if os.system(command):
        raise RuntimeError('{} failed!'.format(str(command)))
    if delete_folder:
        if os.system('rm -r {}'.format(source_dir)):
            raise RuntimeError('deleting folder {} failed!'.format(
                str(source_dir)))
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

    return [o for o in out if o]  #filter out empty lists


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

def get_fraction_of_landmarkAscii(frac, path):
    'returns fraction of landmarkAscii files defined in path'
    f = os.path.basename(path)
    celltype = f.split('.')[-2]
    positions = scp.read_landmark_file(path)
    pdf = pd.DataFrame({'positions': positions, 'label': celltype})
    if len(pdf) == 0:  # cannot sample from empty pdf
        return pdf
    if frac >= 1:
        return pdf
    else:
        return pdf.sample(frac=frac)


def get_fraction_of_landmarkAscii_dir(frac, basedir=None):
    'loads all landmarkAscii files in directory and returns dataframe containing'\
    'position and filename (without suffix i.e. without .landmarkAscii)'
    out = []
    for f in os.listdir(basedir):
        if not f.endswith('landmarkAscii'):
            continue
        out.append(get_fraction_of_landmarkAscii(1, os.path.join(basedir, f)))

    return pd.concat(out).sample(frac=frac).sort_values('label').reset_index(
        drop=True)

def select_cells_that_spike_in_interval(
    sa,
    tmin,
    tmax,
    set_index=[
        'synapse_ID', 'synapse_type'
    ]):
    pdf = sa.set_index(list(set_index))
    pdf = pdf[[c for c in pdf.columns if c.isdigit()]]
    pdf = pdf[((pdf >= tmin) & (pdf < tmax)).any(axis=1)]
    cells_that_spike = pdf.index
    cells_that_spike = cells_that_spike.tolist()
    return cells_that_spike
def get_fraction_of_landmarkAscii(frac, path):
    'returns fraction of landmarkAscii files defined in path'
    f = os.path.basename(path)
    celltype = f.split('.')[-2]
    positions = scp.read_landmark_file(path)
    pdf = pd.DataFrame({'positions': positions, 'label': celltype})
    if len(pdf) == 0:  # cannot sample from empty pdf
        return pdf
    if frac >= 1:
        return pdf
    else:
        return pdf.sample(frac=frac)


def get_fraction_of_landmarkAscii_dir(frac, basedir=None):
    'loads all landmarkAscii files in directory and returns dataframe containing'\
    'position and filename (without suffix i.e. without .landmarkAscii)'
    out = []
    for f in os.listdir(basedir):
        if not f.endswith('landmarkAscii'):
            continue
        out.append(get_fraction_of_landmarkAscii(1, os.path.join(basedir, f)))

    return pd.concat(out).sample(frac=frac).sort_values('label').reset_index(
        drop=True)

def select_cells_that_spike_in_interval(
    sa,
    tmin,
    tmax,
    set_index=[
        'synapse_ID', 'synapse_type'
    ]):
    pdf = sa.set_index(list(set_index))
    pdf = pdf[[c for c in pdf.columns if c.isdigit()]]
    pdf = pdf[((pdf >= tmin) & (pdf < tmax)).any(axis=1)]
    cells_that_spike = pdf.index
    cells_that_spike = cells_that_spike.tolist()
    return cells_that_spike