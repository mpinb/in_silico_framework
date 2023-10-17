import Interface as I
import warnings
import project_specific_ipynb_code.biophysical_models.RW_analysis
import importlib
importlib.reload(project_specific_ipynb_code.biophysical_models.RW_analysis)
from  project_specific_ipynb_code.biophysical_models.RW_analysis import read_all
import model_data_base.IO.LoaderDumper.dask_to_parquet


# default setup is as follows:
# create a model database with one sub model data base as subkey
# each sub model data base is initialized as biophysics_simulator mdb, i.e. has the keys get_SImulator, ...
# the sub database contains the key outdir_{description}

def init(mdb, key, client = None, outdir = None, return_list = []):
    assert(client is not None)
    if outdir is None:
        outdir = mdb['outdir_'.format(key)]
    n_particles = len(I.os.listdir(outdir))
    l = Load(client, outdir, n_particles = n_particles)
    init_RW_exploration(mdb, l , key)
    

def get_dtype(df):
    return df.dtypes

def map_bool_to_str(df):
    columns = [c for c in df.columns if df.dtypes[c] == bool]
    for c in columns:
        df[c] = df[c].map(str)
    return df

class Load:
    def __init__(self, client, path, n_particles_start = 0, n_particles_end = 1000):
        self.path = path
        self.delayeds = read_all(path, n_particles_start = n_particles_start, n_particles_end = n_particles_end)
        self.futures = client.compute(self.delayeds)
        self.client = client
        
        self.df = None

    def get_df(self):
        if self.df is None:
            # constructs a dask dataframe with monotonously increasing index and known divisions
            futures = self.futures
            # check if some futures return 'empty', which indicates that no simulations for this seedpoint have been performed
            empty_list = self.client.gather(self.client.map(lambda x: isinstance(x, str) and x == 'empty', futures))
            if any(empty_list):
                warnings.warn('No simulations found for some seedpoints! Skipping these seedpoints.')
            futures = [f for f, e in zip(futures, empty_list) if not e]
            futures = self.client.map(map_bool_to_str, futures)
            meta_ = futures[0].result().head(0)            
            lengths = self.client.gather(self.client.map(len, futures))
            cumulative_lengths = I.np.cumsum(lengths)
            divisions = [0] + cumulative_lengths.tolist()
            df = tuple(divisions)
            futures = self.client.map(set_range_index, list(zip(futures,divisions)))
            self.df = I.dask.dataframe.from_delayed(futures, meta = meta_)
            self.df.divisions = divisions
        return self.df
    
    def get_futures(self):
        return self.futures
    
    def set_index(df_pd):
        return df_pd.set_index((df_pd.particle_id.astype('str') + '/' + df_pd.iteration.astype('str')), drop = True)

def set_range_index(df_start_tuple):
    df, start = df_start_tuple
    stop = start+len(df)
    df.index = I.pd.RangeIndex(start = start, stop = stop)
    return df

def init_RW_exploration(client, target_mdb, data, name):
    # copy_simulator_setup(simulator_mdb, m)
    futures = data.futures
    df = data.get_df() # Load.get_df(data) # should be: data.get_df()
    target_mdb.setitem(name, df, 
                       dumper = model_data_base.IO.LoaderDumper.dask_to_parquet, 
                       client = client)
    target_mdb.setitem(name + '_inside', df[df.inside == 'True'], 
                       dumper = model_data_base.IO.LoaderDumper.dask_to_parquet, 
                       client = client)
    
def copy_simulator_setup(source_mdb, target_mdb):
    target_mdb.setitem('params', source_mdb['params'], dumper = I.dumper_pandas_to_pickle)
    target_mdb.setitem('get_fixed_params', source_mdb['get_fixed_params'], dumper = I.dumper_to_cloudpickle)
    target_mdb.setitem('get_Simulator', source_mdb['get_Simulator'], dumper = I.dumper_to_cloudpickle)
    target_mdb.setitem('get_Evaluator', source_mdb['get_Evaluator'], dumper = I.dumper_to_cloudpickle)
    target_mdb.setitem('get_Combiner', source_mdb['get_Combiner'], dumper = I.dumper_to_cloudpickle)
    target_mdb.create_managed_folder('morphology', raise_ = False)
    I.shutil.copy(source_mdb['morphology'].get_file('.hoc'), target_mdb['morphology'])
    
def get_dtype(df):
    return df.dtypes

def map_bool_to_str(df):
    columns = [c for c in df.columns if df.dtypes[c] == bool]
    for c in columns:
        df[c] = df[c].map(str)
    return df