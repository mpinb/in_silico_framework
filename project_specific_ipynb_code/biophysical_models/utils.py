import Interface as I 
import cloudpickle 
import os
import dask
from copy import deepcopy

from biophysics_fitting.hay_complete_default_setup import get_feasible_model_params
import project_specific_ipynb_code.hot_zone
from biophysics_fitting.utils import get_inner_sec_dist_dict
from biophysics_fitting.utils import get_inner_section_at_distance

from sklearn.decomposition import PCA
from project_specific_ipynb_code.biophysical_models.RW_analysis import hz_current_columns

def check_example_vt(data,  mdb_example_vt_folder, morphology, p = None):
    savedir = os.path.join(mdb_example_vt_folder, data.name, morphology)
    if not os.path.exists(savedir):
        print(f'No example voltage traces available for {morphology}')
        return
    p_names = os.listdir(savedir)
    print(f'{len(p_names)} available voltage traces for {morphology}:')
    print(*p_names)
    if p is None: 
        return
    if not isinstance(p, int) and not isinstance(p, I.np.int64):
        p = p.name 
    if str(p) not in p_names: 
        print('Voltage traces for given p is not available, run get_example_vt to run and save')
        return
    print('Voltage traces for given p is available! Run get_example_vt to retrieve')
    

def get_example_vt(data,  mdb_example_vt_folder, morphology, p, client):
    '''function to easily run and/or retrieve voltage traces for given p
    needs data object (databases module) with simulator and name.
    For retrieving data, it is sufficient to just provide the index of the parameter vector (p.name)'''
    if isinstance(p, int): # retrieve data from param index
        print('Retrieving')
        savepath = os.path.join(mdb_example_vt_folder, data.name, morphology, str(p))
        with open(savepath, 'rb') as f:
            return cloudpickle.load(f)
    s = data.s[morphology]        
    param_id = p.name
    assert(param_id is not None)
    savedir = os.path.join(mdb_example_vt_folder, data.name, morphology)
    savepath = os.path.join(savedir,str(param_id))
    if os.path.exists(savepath):
        print('Exists! Retrieving')
        with open(savepath, 'rb') as f:
            return cloudpickle.load(f)
    if os.path.exists(savepath + '.running'):
        print('Already running. Wait and run again to retrieve.')
        return
    os.makedirs(savedir, exist_ok = True)
    print('Doesn\'t exist, running with dask. Run this cell again to retrieve.')
    f = client.submit(run_example_vt_helper, s,p,savepath)
    I.distributed.fire_and_forget(f)
    
    
def run_example_vt_helper(s, p, savepath):
    with open(savepath + '.running', 'wb') as f:
            cloudpickle.dump(p, f)
    voltage_traces = s.run(p)
    with open(savepath + '.running', 'wb') as f:
        cloudpickle.dump(voltage_traces, f)
    os.rename(savepath + '.running', savepath)  
    
    
    
#function to sample the dask dataframe (data.ddf_dict)
def grab_models_as_pd_df(morph, seed, data, len_ = None, n_to_return = 10000): 
    ''' if data object doesn't have df_dict atrr, need to give len (the length of dff_dict[morph]) '''
    if hasattr(data, 'df_dict'): 
        len_ = len(data.df_dict[morph])
    df = data.ddf_dict[morph]
    frac = n_to_return/len_ * 1.5
    if frac < 0.001: 
        frac = 0.001
    df = df.sample(frac = frac, random_state=seed)
    df = df.compute()
    df = df.head(n_to_return)
    return df



def get_df_with_inside_col_for_stim(df, stim_name, objective_columns): 
    '''function to return df with objective columns and an additional inside column for a particular stim'''
    df_out = df[objective_columns + ['step_size']].copy()
    boundary = 3.2 
    if 'Step' in stim_name: 
        boundary = 4.5
    df_out[stim_name + '_inside'] = df_out[objective_columns].apply(abs, axis = 1).apply(max , axis = 1).apply(lambda x: x<=boundary)
    return df_out



### various utils for setting up mdb with modified simulator etc. 
def get_modified_feasible_model_params():
    params = get_feasible_model_params().drop('x', axis = 1)
    params.index = 'ephys.' + params.index
    params = params.append(I.pd.DataFrame({'ephys.SKv3_1.apic.slope': {'min': -3, 'max': 0},
                                           'ephys.SKv3_1.apic.offset': {'min': 0, 'max': 1}}).T)
    params = params.append(I.pd.DataFrame({'min': 0.5, 'max': 3}, index = ['scale_apical.scale']))
    params = params.append(I.pd.DataFrame({'ephys.Ih.apic.linScale': {'min': 1.5, 'max': 10},
                                           'ephys.Ih.apic.max_g': {'min': 0.003, 'max': 0.0150}}).T)
    params = params.sort_index()
    index_new = []
    for p in params.index:
        if 'CaDynamics_E2' in p:
            p = p.replace('CaDynamics_E2', 'CaDynamics_E2_v2')
        index_new.append(p)
    params['index_new'] = index_new
    params = params.set_index('index_new', drop = True)
    return params 

def scale_apical(cell_param, params):
    assert(len(params) == 1)
    cell_param.cell_modify_functions.scale_apical.scale = params['scale']
    return cell_param

def get_fixed_params(mdb_setup):
    fixed_params = mdb_setup['fixed_params']
    fixed_params['morphology.filename'] = mdb_setup['morphology'].get_file('hoc')
    return fixed_params

def make_sure_hay_evaluator_did_not_run():
    import biophysics_fitting.hay_evaluation
    assert biophysics_fitting.hay_evaluation.is_setup() == False
    
def import_Interface_first(fun):
    def helper(*args, **kwargs):
        import Interface
        return fun(*args, **kwargs)
    return helper

def get_bifurcation_distance(cell):
    d = project_specific_ipynb_code.hot_zone.Dendrogram(cell)
    d._compute_main_bifurcation_section()
    return d.main_bifur_dist
    
def get_outsidescale_sections(cell):
    inner_sections = get_inner_sec_dist_dict(cell)
    outside_scale_sections = [lv for lv, sec in enumerate(cell.sections) 
                              if sec.label == 'ApicalDendrite' and sec not in inner_sections.values()]
    return outside_scale_sections

def remove_from_vt(tVec, vList, tstart, tend, shift = 0):
    mask = (tVec < tstart) | (tVec > tend) 
    tVec = tVec[mask]
    vList = [v[mask] for v in vList]
    return tVec + shift, vList

def cut_from_vt(tVec, vList, tstart, tend, shift = 0):
    mask = (tVec < tstart) | (tVec > tend) 
    tVec[tVec > tend] = tVec[tVec > tend] - tend + tstart
    tVec = tVec[mask]
    vList = [v[mask] for v in vList]
    return tVec , vList

# first burst
def prepare_vt_to_select_one_burst(vt, delay = None):
    if not 'BAC.hay_measure' in vt: 
        return vt
    
    vt_new = deepcopy(vt)
    t, (v1,v2) = cut_from_vt(deepcopy(vt_new['BAC.hay_measure']['tVec']), 
                             deepcopy(vt_new['BAC.hay_measure']['vList']), 
                             295+delay, 600+delay)
    vt_new['BAC1.hay_measure'] = {}
    vt_new['BAC1.hay_measure']['tVec'] = t
    vt_new['BAC1.hay_measure']['vList'] = [v1,v2]

    t, (v1,v2) = remove_from_vt(deepcopy(vt['BAC.hay_measure']['tVec']), 
                                deepcopy(vt['BAC.hay_measure']['vList']), 
                                295, 295+delay, shift = -delay)
    vt_new['BAC2.hay_measure'] = {}
    vt_new['BAC2.hay_measure']['tVec'] = t
    vt_new['BAC2.hay_measure']['vList'] = [v1,v2]
    
    del vt_new['BAC.hay_measure']
    
    return vt_new


### for PCA analysis 


def find_label(list_, search_key_list): 
      return [item for item in list_ if all([search_key in item for search_key in search_key_list])] 

def get_PC_explained_variance_plot(dict_with_pca_objects):
    for morph in dict_with_pca_objects.keys():
        pca = dict_with_pca_objects[morph] 
        I.plt.plot(pca.explained_variance_ratio_, label=morph)
    x_ticklabels = [f'PC{i}' for i in range(1,len(pca.explained_variance_ratio_)+1)]
    ax = I.plt.gca()
    ax.set_xticks(range(len(pca.explained_variance_ratio_)))
    ax.set_xticklabels(range(1,len(pca.explained_variance_ratio_)+1))
    ax.legend(shadow=True, fancybox=True)
    
def visualize_PC_components(dict_with_pca_objects, columns, abs_ = False, print_var_ex = True, xtick_labels = None): 
    n_components = len(list(dict_with_pca_objects.values())[0].components_)
    fig, axes = I.plt.subplots(1,n_components, figsize = (8*n_components, 6))
    for morph in dict_with_pca_objects.keys(): 
        pca = dict_with_pca_objects[morph] 
        plot_from_PCA_obj(axes, pca, columns, morph = morph, abs_ = abs_, 
                          print_var_ex = print_var_ex, xtick_labels = xtick_labels)
    fig.show()
        
        
def plot_from_PCA_obj(axes, pca, columns, morph = None, abs_ = False, print_var_ex = True, c = None, 
                      xtick_labels = None):
    '''if not given xticks, assumes ephys.actual_label.etc notation to get the actual labels'''
    n_components = len(pca.components_)
    for i in range(n_components):
        if abs_: 
            axes[i].plot(abs(pca.components_[i]), label=morph)
        else: 
            axes[i].plot(pca.components_[i], label=morph)
            if c: 
                axes[i].plot(pca.components_[i], label=morph, c = c)
        axes[i].set_title(f'PC{i}')
    for ax in axes:
        if not xtick_labels: 
            xtick_labels = [clm.split('.')[1] for clm in columns]
        ax.set_xticks(range(len(xtick_labels)))
        ax.set_xticklabels(xtick_labels, rotation = 90)
        ax.legend(shadow=True, fancybox=True)
    if print_var_ex: 
        print(morph)
        print(f'Total explained variance: {sum(pca.explained_variance_ratio_)}')
        print(f'Components:{pca.explained_variance_ratio_}' )
        print(' ')
        
        
def get_PCA_objects(df_dict, n_components):    
    '''needs dict of df with morph as keys and df with values to do the PCA on
    returns dict with pca objects'''

    pcas = {}
    for morph in df_dict.keys(): 
        pca = PCA(n_components=n_components)
        pca.fit(df_dict[morph].values)
        pcas[morph] = pca
    return pcas


def should_retrieve(savepath, rerun): 
    #if it exists, retrieve (unless rerun)
    if I.os.path.exists(savepath): 
        if rerun: 
            return False 
        else:
            return True
    return False 


#ideally the name would data.name and df_dict data .df_dict (or ddf_dict)
def data_to_pca_output(df_dict = None, name = None, selected_columns = None, n_components = 2, 
                      mdb_pca_objects_folder = None, abs_ = False, print_var_ex = True, normalize_fun = None, rerun = False):
    '''returns dict with pca objects and plots the components. if the pca objects were already calculated 
    and saved in the specified mdb, only retrieves. in this case df_dict is not necessary.'''

    # label to save, assumes that the columns are names with the convention "general_cat.detailed_label"
    assert name != None, 'Need to provide name'
    label = '_'.join([name, selected_columns[0].split('.')[0], f'{n_components}_components'])
    print(label)
    savepath = mdb_pca_objects_folder.join(label)
    retrieve = should_retrieve(savepath, rerun)
    if retrieve:
        print('retrieving')
        with open(savepath, 'rb') as f:
            pcas = I.cloudpickle.load(f)
    else: 
        assert df_dict != None, 'PCA objects not saved, need df_dict to compute '
        # let's only grab the needed columns 
        df_dict_new = {}
        for morph in df_dict.keys():
            if normalize_fun != None: 
#                 df_dict_new[morph] = df_dict[morph][selected_columns].T.apply(normalize_fun).T
                df_dict_new[morph] = normalize_fun(df_dict[morph][selected_columns])
            else: 
                df_dict_new[morph] = df_dict[morph][selected_columns]

        pcas = get_PCA_objects(df_dict_new, n_components)
        with open(savepath, 'wb') as f:
            I.cloudpickle.dump(pcas, f)
            
    visualize_PC_components(pcas, columns = selected_columns, 
                            abs_ = abs_, print_var_ex = print_var_ex)
    
    return pcas


def min_max_normalize_from_given_ranges(df, params_range: I.pd.DataFrame = None):
    df_out = df.copy()
    for col in params_range.index:
        min_ = params_range['min'][col]
        max_ = params_range['max'][col]
        df_out[col]  = (df_out[col] - min_)/(max_-min_)
    return df_out


