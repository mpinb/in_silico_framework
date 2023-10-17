import Interface as I

params = {}
objectives = {}

class Data:
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)
            
def _get_ddf_RW_exploration_template(mdb, key, selected_keys, columns = None, inside = True, persist = False):
    out = {}
    if inside:
        key = key + '_inside'
    for k in selected_keys:
        out[k] = mdb[k].getitem(key, columns = columns) 
    if persist:
        out = {k:client.persist(ddf) for k, ddf in out.items()}
    m = mdb[k]
    s = m['get_Simulator'](m)
    e = m['get_Evaluator'](m)
    c = m['get_Combiner'](m)
    out_data = Data(ddf_dict = out, params = mdb[k]['params'], s = s, e = e, c = c, param_names = list(mdb[k]['params'].index))
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
mdb = I.ModelDataBase('/gpfs/soma_fs/scratch/abast/results/20230929_RW_exploration_new_Ih_crti_freq_hyperpolarizing')


