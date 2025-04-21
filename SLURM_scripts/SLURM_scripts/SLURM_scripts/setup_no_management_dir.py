import os
import socket
import time
import sys
import Interface 
import torch
from SLURM_scripts import nbrun

rank = int(os.environ['SLURM_PROCID'])
n_cpus = os.environ['SLURM_CPUS_PER_TASK']
scheduler_ip = socket.gethostbyname(os.environ['ISF_MASTER_ADDR'])
scheduler_ip = scheduler_ip.replace('100','102')

command_dask_scheduler = '''bash -ci "source ~/.bashrc; source_3; dask-scheduler --port=38786 --interface=ib0 --dashboard-address=:38787" &'''
command_dask_worker = '''bash -ci "source ~/.bashrc; source_3; dask-worker --nthreads 1  --nprocs {n_cpus} --local-directory $JOB_TMPDIR --memory-limit=100e9 {scheduler_ip}:38786" &'''
command_dask_worker = command_dask_worker.format(n_cpus = n_cpus, scheduler_ip = scheduler_ip)

# just to use torch barrier
os.environ['MASTER_ADDR'] = scheduler_ip
os.environ['RANK'] = str(rank)
os.environ['WORLD_SIZE'] = str(4)
os.environ['MASTER_PORT'] = '2345'
torch.distributed.init_process_group(backend='nccl')

if rank == 0:
    os.system(command_dask_scheduler)
    
os.system(command_dask_worker)

if rank == 0:
    notebook_name = sys.argv[1]
    notebook_kwargs = sys.argv[2]
    notebook_kwargs = eval(notebook_kwargs)

nbrun.run_notebook(notebook_kwargs)
torch.distributed.barrier()
