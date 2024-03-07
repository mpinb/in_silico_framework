import Interface as I

params = {}
objectives = {}

class Data:
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)
            
# PCA plot
def get_index(dataframe, channel):
    '''computes the depolarization or hyperpolarization index'''
    if channel in hyperpo_channels:
        norm = dataframe[hyperpo_channels].sum(axis = 1)
    elif channel in depo_channels:
        norm = dataframe[depo_channels].sum(axis = 1)
    return dataframe[channel] / norm

def get_depolarization_index(dataframe):
    CaHVA = get_index(dataframe, 'BAC_bifurcation_charges.Ca_HVA.ica')
    CaLVA = get_index(dataframe, 'BAC_bifurcation_charges.Ca_LVAst.ica')
    return (CaLVA-CaHVA)/(CaHVA+CaLVA)

def get_hyperpolarization_index(dataframe):
    Im = get_index(dataframe, 'BAC_bifurcation_charges.Im.ik')
    Sk = get_index(dataframe, 'BAC_bifurcation_charges.SK_E2.ik')
    return (Sk-Im)/(Im+Sk)

def augment_ddf_with_PCA_space(ddf, hz_current_columns = None, pca_components = None):
    def _helper(df):
        df['pc0'] = I.np.dot(df[hz_current_columns], pca_components[0])
        df['pc1'] = I.np.dot(df[hz_current_columns], pca_components[1])
        df['depolarization_index'] = get_depolarization_index(df)
        df['hyperpolarization_index'] = get_hyperpolarization_index(df)
        return df
    meta_ = _helper(ddf.head())
    ddf_augmented = ddf.map_partitions(_helper, meta = meta_)
    return ddf_augmented

def augment_ddf_with_mean_error(ddf, objectives = None):
    def _helper(df):
        df['mean_error'] = df[objectives].mean(axis=1)
        df['max_error'] = df[objectives].max(axis=1)
        return df
    meta_ = _helper(ddf.head())
    ddf_augmented = ddf.map_partitions(_helper, meta = meta_)
    return ddf_augmented

hz_current_columns = ['BAC_bifurcation_charges.Ca_HVA.ica',
 'BAC_bifurcation_charges.SK_E2.ik',
 'BAC_bifurcation_charges.Ca_LVAst.ica',
 'BAC_bifurcation_charges.NaTa_t.ina',
 'BAC_bifurcation_charges.Im.ik',
 'BAC_bifurcation_charges.SKv3_1.ik']

pca_components = I.np.array([[  7.63165639e-01,   6.29498003e-01,  -8.63749227e-02,
          2.74177180e-04,  -1.40787230e-02,   1.16839883e-01],
       [  5.24587951e-01,  -5.64428021e-01,   5.25520353e-01,
         -1.39713239e-03,   3.57672349e-01,   4.61019458e-02]])

hz_current_columns_short = [k.split('.')[1] for k in hz_current_columns]

depo_channels = [ 'BAC_bifurcation_charges.Ca_HVA.ica',
                  'BAC_bifurcation_charges.Ca_LVAst.ica',
                  'BAC_bifurcation_charges.NaTa_t.ina']

hyperpo_channels = ['BAC_bifurcation_charges.SK_E2.ik',
                   'BAC_bifurcation_charges.Im.ik',
                   'BAC_bifurcation_charges.SKv3_1.ik']


            
def _get_ddf_RW_exploration_template(mdb, key, name, selected_keys, columns = None, inside = True, persist = False, 
                                     augment_success_rates = False, 
                                     augment_new_energy_metrics = False,
                                     augment_PCA = False,
                                     augment_PCA_components = None,
                                     augment_PCA_hz_current_columns = None,
                                     augment_mean_error = False,
                                     augment_mean_error_objectives = None):
    out = {}
    s = {}
    e = {}
    c = {}
    m = {}
    if inside:
        key = key + '_inside'
    if augment_success_rates:
        assert inside
    for k in selected_keys:
        out[k] = mdb[k].getitem(key, columns = columns) 
        if augment_PCA: # needs to be done before new_energy metrics augmentation or dask will raise an error about a column order mimatch
            errmsg = 'if augment_PCA is true, augment_PCA_hz_current_columns and augment_PCA_components need to be set. Default values are: \n'
            errmsg += 'hz_current_columns: {} \n \n'.format(hz_current_columns)
            errmsg += 'pca_components: {} \n \n'.format(pca_components)
            assert augment_PCA_components is not None
            assert augment_PCA_hz_current_columns is not None
            out[k] = augment_ddf_with_PCA_space(out[k], pca_components = augment_PCA_components,
                                                hz_current_columns = augment_PCA_hz_current_columns)
        if augment_mean_error:
            out[k] = augment_ddf_with_mean_error(out[k], objectives = augment_mean_error_objectives)
        if augment_success_rates:
            out[k] = I.dask.dataframe.concat([out[k], mdb[k].getitem(key + '_augment_success_rates')], axis = 1)
        if augment_new_energy_metrics:
            assert inside
            out[k] = I.dask.dataframe.concat([out[k], mdb[k].getitem(key + '_augment_new_energy_metrics')], axis = 1)
        m[k] = mdb[k]
        s[k] = mdb[k]['get_Simulator'](mdb[k])
        e[k] = mdb[k]['get_Evaluator'](mdb[k])
        c[k] = mdb[k]['get_Combiner'](mdb[k])
    if persist:
        out = {k:client.persist(ddf) for k, ddf in out.items()}
    out_data = Data(ddf_dict = out, 
                    params = mdb[k]['params'], 
                    s = s, 
                    e = e, 
                    c = c, 
                    m = m, 
                    param_names = list(mdb[k]['params'].index),
                    name = name,
                    mdb = mdb,
                    key = key)
    return out_data


## The database below contains:
# - the genetic optimization algorithm models, generated in py2 for the energy preprint
# - the genetic optimization algorithm models, generated in py3 for the hot zone paper. These modells are additionally constrained for a second BAC stimulus
mdb_meeting_mickey = I.ModelDataBase('/gpfs/soma_fs/scratch/abast/results/20230301_meeting_mickey')

## The database below contains:
# - 'run1', which was based on the py3 models from above, utilizing the model with the lowest overall deviation for each morphology
#       - WR71 2.254335260115607
#       - 84 2.166993482361211
#       - 89 2.2841984841982517
#       - WR64 2.2584754497108372
#       - 91 2.155247191246019
#       - 88 2.4349986349987858
#       - 85 2.291491383640009
# - 'run2_from_tip_of_run_1': a new random walk, this time initialized from the model that is the most left in the PCA space of run1
# - (NI) 'adaptive_step_size': as above, but step size is automatically adapted for each seed to achieve a 50% success rate
# - 'linked_views_v1': a new random walk, initialized by selecting models with linked views from 'run1' and 'run2_from_tip_of_run_1'. Selected were the models by plotting
#                          energy efficiency against each dendritic conductance and selecting those 
mdb_RW_exploration = I.ModelDataBase('/gpfs/soma_fs/scratch/abast/results/20230628_start_RW_exploration_on_all_morphologies')

def get_ddf_RW_exploration_on_all_morphologies__linked_views_v1(columns = None, inside = True, persist = False):
    selected_keys = ['linked_views_v1_SK_E2_min_energy',
     'linked_views_v1_Kv3.1_min_energy',
     'linked_views_v1_Im_min_energy',
     'linked_views_v1_Ca_LVAst_min_energy',
     'linked_views_v1_Ca_HVA_min_energy',
     'linked_views_v1_Na_min_energy']    
    out = {}
    for k in selected_keys:
        if inside:
            k_ = k + "_inside"
        else:
            k_ = k
        out[k] = mdb_RW_exploration['WR64'].getitem(k_, columns = columns) 
    if persist:
        out = {k:client.persist(ddf) for k, ddf in out.items()}
    return out

get_ddf_RW_exploration_on_all_morphologies__run1 = I.partial(_get_ddf_RW_exploration_template,
                                                             mdb_RW_exploration, 
                                                             'run1')

get_ddf_RW_exploration_on_all_morphologies__run2_from_tip_of_run_1 = I.partial(_get_ddf_RW_exploration_template,
                                                             mdb_RW_exploration, 
                                                             'run2_from_tip_of_run_1')

## The database below contains
# run1: initialized at the same seed points as run1 in the database above, but additionally Ih is parameterized, and the crit freq stimuli were additionally evaluated, but not used as constraints
#         These simulations resulted in models for which the critical frequency was well constrained for ['WR64', '89', '91', 'WR71', '85', '88', '84']
# run_expansion: as run1, but the RW algorithm was modified to enforce suggested points increase distance to the seed point. Selected morphologies were
#         WR64 (here, I know that the possibility space covers the whole PCA space) and '85', '88', '84', which are the morphologies, for which models with
#         well constrained critical frequedncy had not been previously found.
mdb_RW_exploration_new_Ih = I.ModelDataBase('/gpfs/soma_fs/scratch/abast/results/20230918_RW_exploration_new_Ih') # for 5 morphologies, models with ['WR64', '85', '88', '84']


get_ddf_RW_exploration_new_Ih__run1 = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih, 
                                                 'run1',
                                                 selected_keys = ["WR71",  "84",  "89",  "WR64",  "91",  "88",  "85"])

get_ddf_RW_exploration_new_Ih__run_expansion = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih, 
                                                 'run_expansion',
                                                 selected_keys = ['WR64', '85', '88', '84'])

## The database below contains
# - (NI, I running) run1: initialized from models in run1 in the database above with a seed point that fulfill the critical frequency constraints.
#         this time including these as constraints of the possibility space. 
#         morphologies are: ['WR64', '89', '91', 'WR71', '88']
mdb_RW_exploration_new_Ih_crit_freq_hyperpolarizing = I.ModelDataBase('/gpfs/soma_fs/scratch/abast/results/20230929_RW_exploration_new_Ih_crti_freq_hyperpolarizing')

## The database below contains
# - run1: initialized from models in run1 in the database above with a seed point that fulfill the critical frequency constraints.
#         this time including these as constraints of the possibility space. 
#         morphologies are: ['WR64', '89', '91', 'WR71', '88']
mdb_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing = I.ModelDataBase('/gpfs/soma_fs/scratch/abast/results/20231018_RW_exploration_new_Ih_2BAC_step_crit_freq_chirp_hyperpolarizing')

get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_run1 = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing, 
                                                 'run1',
                                                 'get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_run1',
                                                 selected_keys = ['WR71'])

get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_run2 = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing, 
                                                 'run2',
                                                 'get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_run2',
                                                 selected_keys = ['WR71'])

get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_run3 = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing, 
                                                 'run3',
                                                 'get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_run3',
                                                 selected_keys = ['WR71'])

get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_run1 = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing, 
                                                 'noAtt_run1',
                                                 'get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_run1',
                                                 selected_keys = ['WR64','WR71','88','89','91'])

get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1 = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing, 
                                                 'noAtt_cf_fixed_run1',
                                                 'get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1',
                                                 selected_keys = ['WR64','WR71','88','89','91'])

get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1_20231226 = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing, 
                                                 'noAtt_cf_fixed_run1_20231226',
                                                 'get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1_20231226',
                                                 selected_keys = ['WR64','WR71','88','89','91'])

get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1_20231227 = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing, 
                                                 'noAtt_cf_fixed_run1_20231227',
                                                 'get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1_20231227',
                                                 selected_keys = ['WR64','WR71','88','89','91'])

get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1_20231228 = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing, 
                                                 'noAtt_cf_fixed_run1_20231228',
                                                 'get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1_20231228',
                                                 selected_keys = ['WR64','WR71','88','89','91'])

get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1_20231228 = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing, 
                                                 'noAtt_cf_fixed_run1_20231228',
                                                 'get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1_20231228_final',
                                                 selected_keys = ['WR64','WR71','88','89','91'])

get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1_20231228_RW_0_01 = I.partial(_get_ddf_RW_exploration_template,
                                                 mdb_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing, 
                                                 'noAtt_cf_fixed_run1_20231228_RW_WR64',
                                                 'get_ddf_RW_exploration_new_Ih_crit_freq_chirp_hyperpolarizing_no_Att_cf_fixed_run1_20231228_RW_0_01',
                                                 selected_keys = ['WR64'])