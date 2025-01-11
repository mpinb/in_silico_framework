import os
#from six import BytesIO
#from StringIO import StringIO as BytesIO - commented by Rieke during python 2to3 transition, looks weird so I keep it here for reference in case something breaks
#import six.StringIO as BytesIO
import six
import numpy as np
import pandas as pd
from data_base.utils import convertible_to_int, split_file_to_buffers, first_line_to_key
from data_base.dbopen import dbopen


#################################################################
# read synapse and cell activation file
#################################################################
def _process_line_fun(line, n_commas):
    line = line.strip()
    line = line.replace('\t', ',')
    real_n_commas = line.count(',')
    return line + ',' * (n_commas - real_n_commas) + '\n'


def _replace_commas(f, n_commas, header, skiprows=1):
    '''robert was using mixed delimiters. this normalizes a file.'''
    f2 = six.StringIO()
    f.seek(0)
    header = header + ','.join(
        [str(x) for x in range(n_commas - header.count(','))]) + '\n'
    f2.write(header)
    for line in f.read().split('\n')[skiprows:]:
        if not line.strip():
            continue
        line = _process_line_fun(line, n_commas)
        f2.write(line)
    f2.seek(0)
    return f2


def read_csv_uneven_length(path, n_commas, header=None, skiprows=0):
    '''general function to read in a csv file with varying length data.
    
    args:
        path: path to file
        n_commas: maximum length of fields
    kwargs:
        header: you can provide an alternative header
        skiprows: skip rows at the beginning of the file (e.g. one to skip the 
                    header if you specified one manually)
    '''
    with dbopen(path) as f:
        bla = _replace_commas(f, n_commas, header, skiprows)
    return pd.read_csv(bla, index_col=False)


def _max_commas(path):
    '''calculates the maximum number of delimiters (',' and '\t' in file.'''
    with dbopen(path, 'r') as f:
        text = f.read()
        text = text.replace('\t', ',')  #only , should be used
        commas_linewise = []
        for l in text.split('\n'):
            if not l:
                continue
            comma_at_end = l[
                -1] == ','  # allways assume that line ends with comma
            commas_linewise.append(l.count(',') + int(not comma_at_end))
        max_commas = max(commas_linewise)
    return max_commas

def _read_roberts_csv_uneven_length_helper(path, header, sim_trail_index = 'no_sim_trail_assigned', \
                                           max_commas = None, set_index = True):
    '''general function for reading roberts csv files. 
    Supports vectorized arguments for path and sim_trail_index. If you provide a list for
    sim_trail_index and path, the result will be one big dataframe containing the data
    of all paths specified, normalized with respect to the overall maximum number of 
    delimiters.
    '''
    if isinstance(path, (list, tuple)):
        #checks for the vectorized case
        assert isinstance(sim_trail_index, (list, tuple))
        assert max_commas is not None
    else:
        path = [path]
        sim_trail_index = [sim_trail_index]

    if max_commas is None:
        max_commas = max([_max_commas(p) for p in path])

    def fun(path, sim_trail_index):
        '''read single file'''
        df = read_csv_uneven_length(path, max_commas, header=header, skiprows=1)
        df['sim_trail_index'] = sim_trail_index
        return df

    p_sti_tuples = list(zip(path, sim_trail_index))

    df = pd.concat([fun(p, sti) for p, sti in p_sti_tuples])
    if set_index:
        df.set_index('sim_trail_index', inplace=True)
    return df


def read_pandas_synapse_activation_from_roberts_format(
        path,
        sim_trail_index='no_sim_trail_assigned',
        max_commas=None,
        set_index=True):
    '''reads synapse activation file from simulation and converts it to pandas table'''
    header = 'synapse_type,synapse_ID,soma_distance,section_ID,section_pt_ID,dendrite_label,'
    return _read_roberts_csv_uneven_length_helper(path, header, sim_trail_index,
                                                  max_commas, set_index)


def synapse_activation_df_to_roberts_synapse_activation(sa):
    """Convert a synapse activation dataframe to a dictionary of synapse activations.
    
    :skip-doc:
    
    Args:
        sa (pd.DataFrame): A :ref:`synapse_activation_format` dataframe.
        
    Returns:
        dict: A dictionary of synapse activations.
    
    Example:

        >>> sa = pd.DataFrame({
        ...     'synapse_ID': [1, 2, 3],
        ...     'section_ID': [1, 2, 3],
        ...     'section_pt_ID': [1, 2, 3],
        ...     'synapse_type': ['AMPA', 'GABA', 'NMDA'],
        ...     'soma_distance': [0, 0, 0],
        ...     '0': [1, 2, 3],
        ...     '1': [4, 5, 6],
        ...     '2': [7, 8, 9]
        ... })
        >>> synapse_activation_df_to_roberts_synapse_activation(sa)
        {'AMPA': [(1, 1, 1, [1, 4, 7], 0)],
         'GABA': [(2, 2, 2, [2, 5, 8], 0)],
         'NMDA': [(3, 3, 3, [3, 6, 9], 0)]}

    """
    synapses = dict()
    import six
    for index, values in sa.iterrows():
        if not values.synapse_type in synapses:
            synapses[values.synapse_type] = []
        synTimes = [
            v for k, v in six.iteritems(values)
            if convertible_to_int(k) and not np.isnan(v)
        ]
        tuple_ = values.synapse_ID, values.section_ID, values.section_pt_ID, synTimes, values.soma_distance
        synapses[values.synapse_type].append(tuple_)
    return synapses

def read_pandas_cell_activation_from_roberts_format(path, sim_trail_index = 'no_sim_trail_assigned', \
                                                    max_commas = None, set_index = True):
    '''reads cell activation file from simulation and converts it to pandas table'''
    header = 'presynaptic_cell_type,cell_ID,'
    return _read_roberts_csv_uneven_length_helper(path, header, sim_trail_index,
                                                  max_commas, set_index)


############################################################
# write synapse activation file
############################################################
def write_pandas_synapse_activation_to_roberts_format(path, syn_activation):
    '''save pandas df in a format, which can be understood by the simulator'''
    with dbopen(path, 'w') as outputFile:
        header = '# synapse type\t'
        header += 'synapse ID\t'
        header += 'soma distance\t'
        header += 'section ID\t'
        header += 'section pt ID\t'
        header += 'dendrite label\t'
        header += 'activation times\n'
        outputFile.write(header)

        columns_containing_activation_times = [
            c for c in syn_activation.columns if convertible_to_int(c)
        ]
        for index, row in syn_activation.iterrows():
            line = str(row['synapse_type'])
            line += '\t'
            line += str(row['synapse_ID'])
            line += '\t'
            line += str(row['soma_distance'])
            line += '\t'
            line += str(row['section_ID'])
            line += '\t'
            line += str(row['section_pt_ID'])
            line += '\t'
            line += str(row['dendrite_label'])
            line += '\t'
            activation_times = row[columns_containing_activation_times]
            for c in columns_containing_activation_times:
                t = row[c]
                if np.isnan(t):
                    break
                line += str(t)
                line += ','

            line += '\n'
            outputFile.write(line)


############################################################
# read input mapper summary
############################################################
def read_InputMapper_summary(pathOrBuffer, sep='\t'):
    '''Expects the path to a summary csv file of the Single Cell Mapper,
    returns the tables as pandas tables'''

    def fun(f):
        '''helper function, contains the main functionality, but only accepts Buffer'''
        tables = split_file_to_buffers(f)
        tables = first_line_to_key(tables)
        for name in tables:
            tables[name] = pd.read_csv(tables[name], sep=sep)
        return tables

    try:  #assume it is path
        with dbopen(pathOrBuffer) as f:
            return fun(f)
    except TypeError:  #if it was buffer instead
        return fun(pathOrBuffer)
