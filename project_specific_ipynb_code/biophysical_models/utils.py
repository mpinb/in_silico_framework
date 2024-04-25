import cloudpickle 
import os
import dask

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
#     savedir = mdb_example_vt_folder.join(data.name).join(morphology)
    savedir = os.path.join(mdb_example_vt_folder, data.name, morphology)
    savepath = os.path.join(savedir,str(param_id))
    if os.path.exists(savepath):
        print('Exists! Retrieving')
        with open(savepath, 'rb') as f:
            return cloudpickle.load(f)
    os.makedirs(savedir, exist_ok = True)
    print('Doesn\'t exist, running with dask. Run this cell again to retrieve.')
    d = dask.delayed(run_example_vt_helper(s,p,savepath))
    f = client.compute(d)
    
    
# @dask.delayed
def run_example_vt_helper(s, p, savepath):
    voltage_traces = s.run(p)
    with open(savepath + '.running', 'wb') as f:
        cloudpickle.dump(voltage_traces, f)
    os.rename(savepath + '.running', savepath)  
    
