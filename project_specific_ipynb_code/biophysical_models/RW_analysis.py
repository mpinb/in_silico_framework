import Interface as I

def read_parameters(seed_folder, particle_id, normalized=False, only_in_space = False, only_return_parameters =  True, param_names = None, param_ranges = None):
    df = read_pickle(seed_folder, particle_id)
    if only_in_space:
        df2 = df.dropna(subset = objectives_2BAC + objectives_step)
        df3 = df2[df2[objectives_2BAC].max(axis = 1) < 3.2]
        df4 = df3[df3[objectives_step].max(axis = 1) < 4.5]
        df = df4
    if only_return_parameters:
        df = df[param_names]
    else:
        assert(normalized == False)
    if normalized:
        df = (df-param_ranges['min'])/(param_ranges['max']-param_ranges['min'])
    df['particle_id'] = particle_id
    return df

def read_pickle(seed_folder, particle_id):
    path = I.os.path.join(seed_folder, str(particle_id))
    df_names = [p for p in I.os.listdir(path) if p.endswith('.pickle')]
    df_names = sorted(df_names, key = lambda x: int(x.split('.')[0]))
    dfs = [I.pd.read_pickle(I.os.path.join(path, p)) for p in df_names]
    if len(dfs) == 0:
        return 'empty'
    df = I.pd.concat(dfs).reset_index(drop=True)
    df['iteration'] = df.index
    df['particle_id'] = particle_id
    return df

def read_all(basedir, n_particles_start = 0, n_particles_end = 1000):
    fun = I.dask.delayed(read_pickle)
    ds = [fun(basedir, i) for i in range(n_particles_start, n_particles_end)]
    return ds

class Load:
    def __init__(self, client, path, n_particles = 1000):
        self.path = path
        self.n_particles = n_particles
        self.delayeds = read_all(path, n_particles)
        self.futures = client.compute(self.delayeds)
        
        self.df = None

    def get_df(self):
        if self.df is None:
            self.df = I.dask.dataframe.from_delayed(self.futures)
        return self.df
    
    def get_futures(self):
        return self.futures
    
    
def get_inside_fraction(l):
    df = l.get_df()
    n_models = df.shape[0].compute()
    n_inside = df[df.inside].shape[0].compute()
    frac = n_inside / n_models
    print('n_models: {}, n_inside: {}, frac: {}'.format(n_models, n_inside, frac))