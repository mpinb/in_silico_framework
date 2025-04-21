import pandas as pd

def get_current_ip():
    import socket
    ipadr_ib = socket.gethostbyname(socket.gethostname()).replace('100','102')
    return ipadr_ib

def setup(ipadr_ib, rank, wold_size, local_rank, local_worldsize, machine_id):
    import os
    import torch
    os.environ['MASTER_ADDR'] = ipadr_ib # '10.102.3.201'
    os.environ['MASTER_PORT'] = '1235'
    os.environ['RANK'] = str(rank) # the first, second, ... process participating in the torch process gorup
    os.environ['LOCAL_RANK'] = str(local_rank) # counts from 0 to 4 on each machine
    os.environ['WORLD_SIZE'] = str(wold_size) # how many processes participate in the group = # GPUs in total
    os.environ['LOCAL_WORLD_SIZE'] = str(local_worldsize)
    os.environ['MACHINE_ID'] = str(machine_id)
    os.environ['TORCH_DISTRIBUTED_DEBUG'] = 'DETAIL'
    torch.distributed.init_process_group(backend='nccl')
    
def get_n_workers_per_ip(workers, n):
    '''helper function to get n workers per machine'''
    s = pd.Series(workers)
    out = []
    for name, group in s.groupby(s.str.split(':').str[1]):
        out.append(group.tolist()[:4])
    return out
    return s.groupby(s.str.split(':').str[1]).apply(lambda x: x[:n]) # .tolist()

def submit_train_loop_to_dask(client, train, batch_size = 10000, GPUS_PER_NODE = 4, skip_rank_0 = True):
    workers = client.scheduler_info()['workers'].keys() 
    selected_workers = get_n_workers_per_ip(workers, GPUS_PER_NODE)
    selected_workers_flat = [k for k in selected_workers for k in k if k.split('.')[2] == '3']
    futures = []
    world_size = len(selected_workers_flat)
    rank = 0
    current_ip = get_current_ip()
    selected_workers = [s for s in selected_workers if current_ip in s[0]] + [s for s in selected_workers if current_ip not in s[0]]

    for machine_id, workers_one_server in enumerate(selected_workers):
        local_rank = 0
        for worker in workers_one_server:
            print(worker)
            if skip_rank_0 and rank == 0:
                rank += 1
                local_rank += 1
                continue # we want rank 0 to be in the local process
            print(rank,world_size,local_rank,GPUS_PER_NODE,machine_id)
            future = client.submit(train,current_ip,rank,world_size,local_rank,GPUS_PER_NODE,machine_id,
                    workers = worker, batch_size = batch_size)
            futures.append(future)
            rank += 1
            local_rank += 1
            
    return world_size, futures