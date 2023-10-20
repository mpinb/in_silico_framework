import Interface as I
import torch
import os
from torch.utils.data import DataLoader, Dataset, IterableDataset, random_split

def get_slice_by_rank(len_, use_local_world_size = False):
    import os
    if use_local_world_size:
        RANK = int(os.environ['RANK'])
        WORLD_SIZE = int(os.environ['WORLD_SIZE'])
        LOCAL_WORLD_SIZE = int(os.environ['LOCAL_WORLD_SIZE'])
        MACHINE_ID = int(os.environ['MACHINE_ID'])
        assert(WORLD_SIZE % LOCAL_WORLD_SIZE == 0)
        chunksize = len_ // (WORLD_SIZE // LOCAL_WORLD_SIZE)
        lower_bound = chunksize*MACHINE_ID
        upper_bound = chunksize*(MACHINE_ID+1)        
    else:
        RANK = int(os.environ['RANK'])
        WORLD_SIZE = int(os.environ['WORLD_SIZE'])
        chunksize = len_ // WORLD_SIZE
        lower_bound = chunksize*RANK
        upper_bound = chunksize*(RANK+1)
    return lower_bound, upper_bound, chunksize

# init

class snsDataset(Dataset):
    def __init__(self, sns, 
                 names = ['AP_DEND', 'SA', 'ISI_SOMA', 'ISI_DEND', 'AP_SOMA', 'VT', 'PARAMS'],
                 mode = 'shared_memory',
                 augment_fun = [],
                 start_row = None,
                 end_row = None,
                 split_by_rank = False,
                 use_local_world_size = False,
                 allow_create_shm = False,
                 train_dataset_size = 0):
        self.sns = sns
        self.names = names
        _, shape, _ = sns._get_metadata_from_name(names[0])
        self.len_whole_dataset = shape[0]
        
        if split_by_rank:
            if start_row is not None or end_row is not None:
                raise NotImplementedError()
        if start_row is None:
            start_row = 0
        if end_row is None:
            end_row = self.len_whole_dataset 
        
        end_row = end_row - train_dataset_size
        
        self.len_ = end_row - start_row

        self.start_row = start_row
        self.end_row = end_row
        
        self.allow_create_shm = allow_create_shm
        if split_by_rank:
            self.start_row, self.end_row, self.len_ = get_slice_by_rank(self.len_, use_local_world_size)
        self.mode = mode
        self.cache = {}
        self.augment_fun = augment_fun

        if train_dataset_size > 0:
            # print('start row of training dataset', self.end_row)
            self.test_dataset = snsDataset(sns, names, 'memory', augment_fun, 
                                        start_row = self.end_row,
                                        end_row = self.end_row + train_dataset_size,
                                        split_by_rank = False,
                                        allow_create_shm = False,
                                        train_dataset_size = 0)
        
    def move_cache_to_gpu(self, device = None):
        self._load_data()
        for name in self.names:
            self.cache[name] = torch.Tensor(self.cache[name]).to(device).float()
    
    def _load_data(self):
        if not self.cache:
            for name in self.names:
                self.cache[name] = self.sns.load(name, 
                                     start_row = self.start_row, 
                                     end_row = self.end_row, 
                                     mode = self.mode,
                                     allow_create_shm = self.allow_create_shm)
    def __len__(self):
        return self.len_
    
    def __getitem__(self, idx):
        self._load_data()
        out = []
        for name in self.names:
            out.append(self.cache[name][idx])
        for fun in self.augment_fun:
            out = fun(out)        
        return out
    
    
# init

def my_vt_expansion(VT, dendritic_compartments):
    out = []
    for lv in dendritic_compartments: # range(VT.shape[1]):
        out.append(torch.Tensor(VT[:,lv,:]))
    return I.np.concatenate(out)

def vectorized_vt_expansion(VT, dendritic_compartments):
    VT_transposed = VT[:,dendritic_compartments,:].transpose(1, 0, 2)
    return VT_transposed.reshape(-1, VT.shape[2])
    #VT_transposed = np.transpose(VT, (0, 2, 1))
    #return VT_transposed.reshape(-1, VT.shape[2])


def normalize_params(PARAMS, max_ = None, min_ = None):
    max_ = I.np.array([200.0, 0.05, 1000.0, 0.05, 1000.0, 0.05, 0.005, 0.001, 0.001, 0.2, 0.01, 0.01, 0.001, 1.0, 1.0, 0.1, 0.1, 0.04, 4.0, 4.0, 0.01, 0.01, 0.01, 0.1, 0.1, 0.04, 1.0, 0.0, 2.0, 2.0, 0.0001, 5e-05, 0.0001, 5.02e-05, 3.0])
    min_ = I.np.array([20.0, 0.0005, 20.0, 0.0005, 20.0, 0.0005, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -3.0, 0.0, 0.0, 3e-05, 2e-05, 3e-05, 2e-05, 0.5])
    return (PARAMS - min_) / (max_ - min_)
    

def expand_400k_BIOPHYSICS_dataset(batch, device = None, dendritic_compartments = None):
    # expands VT 
    assert(device is not None)
    VT = batch[-2]
    dendritic_compartments_full = list(range(VT.shape[1]))
    if dendritic_compartments is None:
        dendritic_compartments = dendritic_compartments_full
    assert(len(VT.shape) == 3)
    n_trials = VT.shape[0]
    PARAMS = batch[-1]
    PARAMS = torch.Tensor(normalize_params(PARAMS)).to(device)

    batch = [torch.Tensor(o).to(device) for o in batch]
    AP_DEND, SA, ISI_SOMA, ISI_DEND, AP_SOMA, _, _ = batch
    
    n_dendritic_compartments = len(dendritic_compartments) # VT.shape[1]
    VT = vectorized_vt_expansion(VT, dendritic_compartments)
    VT = torch.Tensor(VT).to(device)
    
    DENDRITIC_LOCATION = torch.Tensor(range(n_dendritic_compartments)).reshape(-1,1).repeat_interleave(n_trials).to(device)
    DENDRITIC_LOCATION = torch.nn.functional.one_hot(DENDRITIC_LOCATION.long(), num_classes = len(dendritic_compartments_full))
    
    batch = AP_DEND, SA, ISI_SOMA, ISI_DEND, AP_SOMA, VT, PARAMS
    batch = [o.float() for o in batch]
    
    AP_DEND = AP_DEND.repeat(n_dendritic_compartments, 1)
    SA = SA.repeat(n_dendritic_compartments, 1, 1, 1)
    ISI_SOMA = ISI_SOMA.repeat(n_dendritic_compartments, 1)
    ISI_DEND = ISI_DEND.repeat(n_dendritic_compartments, 1)
    AP_SOMA = AP_SOMA.repeat(n_dendritic_compartments, 1)
    PARAMS = PARAMS.repeat(n_dendritic_compartments, 1)
    #      SA, VT, AP_SOMA, AP_DEND, ISI_SOMA, ISI_DEND, PARAMS, DEND_LOCATION   # convention of how data is ordered
    return SA, VT, AP_SOMA, AP_DEND, ISI_SOMA, ISI_DEND, PARAMS, DENDRITIC_LOCATION

# # testing
# snsd = snsDataset(sns, mode = 'shared_memory', augment_fun = [])
# AP_DEND, SA, ISI_SOMA, ISI_DEND, AP_SOMA, VT, PARAMS = snsd[[0,1,2,3]]
# a = my_vt_expansion(VT)
# b = vectorized_vt_expansion(VT)
# I.np.testing.assert_almost_equal(a,b)

def expand_SINGLE_BIOPHYSICS_dataset(batch, dendritic_compartments = [0], device = None):
    batch = [torch.Tensor(b).to(device).float() for b in batch]
    SA, ISI_SOMA, AP_SOMA, VT_SOMA, ISI_DEND, AP_DEND, VT_DEND = batch

    #      SA, VT, AP_SOMA, AP_DEND, ISI_SOMA, ISI_DEND, PARAMS, DEND_LOCATION   # convention of how data is ordered
    if len(dendritic_compartments) != 1:
        raise NotImplementedError()
    
    if dendritic_compartments[0] == 0:
        VT = VT_SOMA
    elif dendritic_compartments[152] == 0: # doublecheck dend is really 147
        VT = VT_DEND
    else:
        raise ValueError('dendritic location not contained in dataset')
        
    return SA, VT, AP_SOMA, AP_DEND, ISI_SOMA, ISI_DEND, None, None



def get_default_dataset(dataset_name, mode = 'memmap', dendritic_compartments = [0], device = None, 
                        split_by_rank = True, train_dataset_size = 0):
    mdb = I.ModelDataBase('/gpfs/soma_fs/scratch/abast/results/20230920_create_ANN_training_dataset_for_hypernetwork_training/')    
    if dataset_name == 'SINGLE_BIOPHYSICS':
        sns = mdb['original_dataset_chantal_dinuka']
        snsd = snsDataset(sns, 
                      mode = mode, 
                      allow_create_shm = True,
                      split_by_rank = split_by_rank, # load only a 1/world_size fraction of the dataset per worker
                      augment_fun = [I.partial(expand_SINGLE_BIOPHYSICS_dataset, 
                                               device = device,
                                               dendritic_compartments = dendritic_compartments)],
                      names = ['SA', 'ISI_SOMA', 'AP_SOMA', 'VT_SOMA', 'ISI_DEND', 'AP_DEND', 'VT_DEND'],
                      train_dataset_size = train_dataset_size)          
    elif dataset_name == '400k_BIOPHYSICS':
        sns = mdb['shared_numpy_store2_fixed']
        snsd = snsDataset(sns, 
                      mode = mode, 
                      allow_create_shm = True,
                      split_by_rank = split_by_rank,
                      augment_fun = [I.partial(expand_400k_BIOPHYSICS_dataset, 
                                               device = device,
                                               dendritic_compartments = dendritic_compartments)],
                      names = ['AP_DEND', 'SA', 'ISI_SOMA', 'ISI_DEND', 'AP_SOMA', 'VT', 'PARAMS'],
                      train_dataset_size = train_dataset_size)
    return snsd


# init

# the Datloader object has a major problem, which is that the __getitem__ method is called sequentially
# which results in low performance (20000 funciton calls for getting 20000 samples). There apparently
# is no way (documented / easy) to make pyotch call getitem with a list of indices instead

# Here, implement an IterableDataset instead and make it such that it returns a random batch of the defined size
# upon __next__

def chunkify(lst, chunk_size):
    return [lst[i:i+chunk_size] for i in range(0, len(lst), chunk_size)]

## this version assumes the dataset has full length (i.e. is not split per machine or worker)
# def compute_batch_indices(len_, batch_size):
#     arr = I.np.array(range(len_))
#     I.np.random.shuffle(arr)
#     out = chunkify(arr, batch_size)
#     ws = torch.distributed.get_world_size()
#     r = torch.distributed.get_rank()
#     return [I.np.array_split(arr, ws)[r] for arr in out]  

## this version assumes the dataset is split per machine or worker)
def compute_batch_indices(len_, batch_size):
    arr = I.np.array(range(len_))
    I.np.random.shuffle(arr)
    ws = torch.distributed.get_world_size()
    out = chunkify(arr, batch_size//ws)
    return out
    r = torch.distributed.get_rank()
    return [I.np.array_split(arr, ws)[r] for arr in out]  

class DatasetToIterableDataset(IterableDataset):
    def __init__(self, dataset, batch_size = 1000, augment_fun = []):
        self.dataset = dataset
        self.len_data = len(dataset)
        self.batch_size = batch_size  
        self.batch_indices = []
        self.augment_fun = augment_fun
        
    def __iter__(self):
        print('computing batch indices')        
        self.batch_indices = compute_batch_indices(self.len_data, self.batch_size)    
        print('done computing batch indices', self.batch_indices[0][:5])        
        return self
        
    def __next__(self):     
        try:
            indices = self.batch_indices.pop()
        except IndexError:
            raise StopIteration
        out = self.dataset[indices]
        for fun in self.augment_fun:
            out = fun(out)
        return out