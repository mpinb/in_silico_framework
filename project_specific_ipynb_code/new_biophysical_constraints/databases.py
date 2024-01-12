import Interface as I

params = {}
objectives = {}

class Data:
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)
            
def _get_ddf_RW_exploration_template(mdb, key, selected_keys, columns = None, inside = True, persist = False):
    out = {}
    s = {}
    e = {}
    c = {}
    m = {}
    if inside:
        key = key + '_inside'
    for k in selected_keys:
        out[k] = mdb[k].getitem(key, columns = columns)
        m[k] = mdb[k]
        s[k] = mdb[k]['get_Simulator'](mdb[k])
        e[k] = mdb[k]['get_Evaluator'](mdb[k])
        c[k] = mdb[k]['get_Combiner'](mdb[k])
    if persist:
        out = {k:client.persist(ddf) for k, ddf in out.items()}
    out_data = Data(ddf_dict = out, params = mdb[k]['params'], s = s, e = e, c = c, param_names = list(mdb[k]['params'].index))
    return out_data


# mdb_crit_numspike_err_new_Ih contains: 
# 'the_satisfactory_models': models constrained for bAP and 2BAC, crit freq numspike error with parameterized Ih distribution. these are not 
mdb_crit_numspike_err_new_Ih = I.ModelDataBase('/gpfs/soma_fs/scratch/saka/results/20230829_run_low_refractory_period_optimization3_two_BAC_crit_freq_ih_distribution_parameterized_v4')
get_ddf_crit_numspike_err_new_Ih = I.partial(_get_ddf_RW_exploration_template, 
                                             mdb_crit_numspike_err_new_Ih,
                                             'the_satisfactory_models')


# mdb_crit_step_chirp contains: 
# 'satisfactory_models_updated_evaluation_20231111': models for '89', '88', 'WR64', '91', 'WR71', contrained for critical 
# frequency, step and chirp.
mdb_crit_step_chirp = I.ModelDataBase('/gpfs/soma_fs/scratch/saka/results/20230919_optimization_crit_freq_step_chirp_ih_distribution_parameterized_start_from_models_with_step_v2')
get_ddf_crit_step_chirp = I.partial(_get_ddf_RW_exploration_template, 
                                             mdb_crit_step_chirp,
                                             'satisfactory_models_updated_evaluation_20231111')


# mbd_new_biophysical_constraints_sat_and_almost_sat_models:
#'current_actually_good_models_WR71': models for WR71 which were optimized for bAP, 2BAC, step, 
# critical frequency, chirp, hyperpolarizing
# (evaluation needs to be updated with the new critical frequency evaluation)
#'models_filtered_for_fixed_crit_freq_evaluation': models for '89', '88', 'WR64', '91', 'WR71' with the latest (20231214) 
# evaluation that were optimized for bAP, 2BAC, step, critical frequency, chirp and 'filtered' for hyperpolarizing 
# objectives besides attenuation.  

# the simulator, evaluator and combiner include all the new biophysical constraints (including attenuation)
mbd_new_biophysical_constraints_sat_and_almost_sat_models = I.ModelDataBase('/gpfs/soma_fs/scratch/saka/results/20231017_models_with_2BAC_step_crit_freq_chirp_hyperpolarizing')
get_ddf_WR71_with_att = I.partial(_get_ddf_RW_exploration_template, 
                                             mbd_new_biophysical_constraints_sat_and_almost_sat_models,
                                             'current_actually_good_models_WR71')
get_ddf_sat_models_without_att = I.partial(_get_ddf_RW_exploration_template, 
                                             mbd_new_biophysical_constraints_sat_and_almost_sat_models,
                                           'models_filtered_for_fixed_crit_freq_evaluation')


# mdb_old_examplary_models_vt contains 'run_old_examplary_models_20231108' and 'eval_run_old_examplary_models_20231108' with respectively the voltage traces
# and evaluation of the 'exemplary_models' from mdb_meeting_mickey

# the simulator, evaluator and combiner include all the new biophysical constraints (including attenuation) but the parameters 
# do not include Ih distribution parameters 
mdb_old_examplary_models_vt = I.ModelDataBase('/gpfs/soma_fs/scratch/saka/results/20231108_thesis_figures')