import os
import numpy as np
import pandas as pd


def generate_output_path(tuple_, prefix=''):
    t0 = tuple_[0]
    t1 = tuple_[1]
    os.path.join(os.path.basename(os.path.dirname(t0)))
    os.path.basename(t0)
    'postcross_'
    os.path.basename(os.path.dirname(t1))
    os.path.basename(t1)
    str(tuple_[2])
    out = os.path.join(os.path.basename(os.path.dirname(t0)), \
                 os.path.basename(t0), \
                 '_'.join(['postcross_', \
                          os.path.basename(os.path.dirname(t1)), \
                          os.path.basename(t1), \
                          'time', str(tuple_[2])]))
    return os.path.join(prefix, out)


#functions to perform time dependent crossing over of two synapse activation files
def _convertible_to_int(x):
    try:
        int(x)
        return True
    except:
        return False


def filter_by_time(pdf, filterfun):
    '''takes a standard synapse activation file returns a new dataframe
    of the same format containing only the activations, for which filterfun returns True
    
    filterfun: 
    function that gets called with every timepoint a synapse gets activated. If it returns True,
    the activation will be kept, if it returns False, it will be omitted.'''
    pdf = pdf.copy()
    relevant_columns = [c for c in pdf.columns if _convertible_to_int(c)]
    for column in relevant_columns:
        pdf[column] = pdf[column].apply(lambda x: x if filterfun(x) else np.NaN)
    return pdf


def _repair_column_identifiers(pdf):
    '''after merging two synapse activation data frames, the format is messed up:
    instead of columns 0,1,2, ... it will have columns 0_x,1_x,2_x, ..., 0_y,1_y,2_y ...
    This function takes such a dataframe, and returns one of a similar format, but with
    reordered synapse activation times and restored column identifiers'''
    relevant_columns = [
        c for c in list(pdf.columns) if _convertible_to_int(c[0])
    ]

    def fun(row):
        #extract relevant columns
        dummy = list(row[relevant_columns])
        length = len(dummy)
        #remove NaN
        dummy = [d for d in dummy if np.isfinite(d)
                ]  # dummy[np.isfinite(dummy)]
        #sort remaining values
        dummy = sorted(dummy)
        #append NaN until original length is reached again
        dummy = list(dummy) + [np.NaN] * (length - len(dummy)
                                         )  #len(list(row[relevant_columns])) -
        #convert to pandas Series
        dummy = {lv: dummy[lv] for lv in range(len(dummy))}
        dummy = pd.Series(dummy)
        return dummy

    labels = [
        'synapse_type', 'synapse_ID', 'soma_distance', 'section_ID',
        'section_pt_ID', 'dendrite_label'
    ]

    new_activation_times = pdf.apply(fun, axis=1)
    ret = pd.concat([new_activation_times, pdf[labels]], axis=1)
    order = labels + list(fun(pdf.iloc[0]).index)
    ret = ret[order]
    return ret[order].dropna(axis=1, how='all')


def merge_synapse_activation(pdf1, pdf2):
    '''merges two synapse activation data tables'''
    try:
        pdf1 = pdf1.drop('sim_trail_index', axis=1)
    except (ValueError,
            KeyError):  # was a ValueError in py2, is KeyError in py3
        pass

    try:
        pdf2 = pdf2.drop('sim_trail_index', axis=1)
    except (ValueError,
            KeyError):  # was a ValueError in py2, is KeyError in py3:
        pass

    x = pdf1.merge(pdf2,
                   on=[
                       'synapse_type', 'synapse_ID', 'soma_distance',
                       'section_ID', 'section_pt_ID', 'dendrite_label'
                   ],
                   how='outer')
    x['synapse_ID'] = x.synapse_ID.astype('int64')
    x['section_ID'] = x.section_ID.astype('int64')
    x['section_pt_ID'] = x.section_pt_ID.astype('int64')
    x = _repair_column_identifiers(x)
    x = x[~np.isnan(x[0])]
    x = x.sort_values(by='synapse_type')
    x = x.reset_index(drop=True)
    return x
