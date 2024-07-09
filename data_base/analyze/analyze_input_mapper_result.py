'''This module contains methods to compare the result of the SingleCellInputMapper to
the neuronet population.'''

import glob
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from data_base.IO.roberts_formats import read_InputMapper_summary
from ..utils import select
from ..analyze import excitatory, inhibitory


def get_neuronet_data(COLUMN='C2',
                      POSTSYNAPTIC_CELLTYPE='L5tt',
                      innervation_table=None):
    if innervation_table is None:
        innervation_table = pd.read_csv(
            '/nas1/Data_regger/AXON_SAGA/Axon2/NeuroNet/cache_Vincent_complete_final/data/synTotal_toC2.csv'
        )
    innervation_table = select(innervation_table,
                               CELLTYPE=POSTSYNAPTIC_CELLTYPE,
                               COLUMN=COLUMN)
    innervation_table.dropna(how='all', inplace=True)
    innervation_per_type = innervation_table.groupby(
        lambda x: x.split('_')[-1], axis=1).apply(lambda x: x.sum(axis=1))
    innervation_per_type.drop(['CELLID', 'CELLTYPE', 'COLUMN'],
                              axis=1,
                              inplace=True)
    innervation_EXCINH = innervation_per_type.groupby(
        lambda x: 'EXC'
        if x in excitatory else 'INH', axis=1).apply(lambda x: x.sum(axis=1))
    return {
        'all': innervation_table,
        'per_type': innervation_per_type,
        'EXCINH': innervation_EXCINH
    }


def get_input_mapper_data(path_to_summmary):
    out = {}
    out['per_type'] = read_InputMapper_summary(path_to_summmary)[
        '# connectivity per cell type representative realization summary'][[
            'Presynaptic cell type', 'Number of synapses'
        ]]
    out['per_type'] = out['per_type'].set_index('Presynaptic cell type')
    out['EXCINH'] = out['per_type'].groupby(
        lambda x: 'EXC' if x in excitatory else 'INH').apply(sum)
    return out


def compare_single_instance_to_neuronet(neuronet_data,
                                        realization_data,
                                        figkwargs={}):
    figs = {}
    for x in neuronet_data['EXCINH']:
        figs[x] = fig = plt.figure(**figkwargs)
        sns.distplot(neuronet_data['EXCINH'][x], ax=fig.add_subplot(111))
        fig.add_subplot(111).axvline(realization_data['EXCINH'].loc[x][0],
                                     c='r')
    for celltype in neuronet_data['per_type'].columns:
        figs[celltype] = fig = plt.figure(**figkwargs)
        sns.distplot(neuronet_data['per_type'][celltype],
                     ax=fig.add_subplot(111))
        try:
            fig.add_subplot(111).axvline(
                realization_data['per_type'].loc[celltype][0], c='r')
        except:
            pass
    return figs


from collections import defaultdict


def realization_data_list_to_dataframe(realization_data_dict):
    out = {}  # defaultdict(lambda: {})
    out_table_names = list(realization_data_dict[list(
        realization_data_dict.keys())[0]].keys())

    for out_table_name in out_table_names:
        out[out_table_name] = {}
        for path in realization_data_dict:
            out[out_table_name][path] = realization_data_dict[path][
                out_table_name].iloc[:, 0]
        out[out_table_name] = pd.DataFrame.from_dict(out[out_table_name],
                                                     orient='index')
    return out


def compare_population_to_neuronet(neuronet_data,
                                   realization_data_df,
                                   figkwargs={}):
    figs = {}
    for x in neuronet_data['EXCINH']:
        figs[x] = fig = plt.figure(**figkwargs)
        sns.distplot(neuronet_data['EXCINH'][x], ax=fig.add_subplot(111))
        sns.distplot(realization_data_df['EXCINH'][x],
                     ax=fig.add_subplot(111),
                     color='r')
    for celltype in neuronet_data['per_type'].columns:
        figs[celltype] = fig = plt.figure(**figkwargs)
        sns.distplot(neuronet_data['per_type'][celltype],
                     ax=fig.add_subplot(111))
        try:
            sns.distplot(realization_data_df['per_type'][celltype],
                         ax=fig.add_subplot(111),
                         color='r')
        except:
            pass
    return figs


def compare_to_neuronet(path_or_paths_to_summary):
    neuronet_data = get_neuronet_data()
    if isinstance(path_or_paths_to_summary, list):
        realization_data_dict = {
            path: get_input_mapper_data(path)
            for path in path_or_paths_to_summary
        }
        realization_data_dict = realization_data_list_to_dataframe(
            realization_data_dict)
        return compare_population_to_neuronet(neuronet_data,
                                              realization_data_dict)
    elif isinstance(path_or_paths_to_summary, str):
        realization_data = get_input_mapper_data(path_or_paths_to_summary)
        return compare_single_instance_to_neuronet(neuronet_data,
                                                   realization_data)
    else:
        raise ValueError("Expected list or str, got %s" %
                         type(path_or_paths_to_summary))


#Example: compare_to_neuronet(glob.glob('/nas1/Data_arco/results/20170214_use_cell_grid_with_soma_at_constant_depth_below_layer_4_to_evaluate_location_dependency_of_evoked_responses/network_embedding/*/*/*summary*.csv'))