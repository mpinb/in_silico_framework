import os
import socket
import time
import sys
from SLURM_scripts import setup_SLURM
from SLURM_scripts.nbrun import run_notebook
from datetime import datetime
import argparse
import distributed

f = open('/gpfs/soma_fs/scratch/abast/output.txt', 'a')
port = 38786
# monkey patch module to use SLURM rank
# setup_SLURM.get_process_number = lambda management_dir: int(os.environ['SLURM_PROCID'])

f.write('{}\n'.format(os.environ['ISF_MASTER_NAME']))
f.flush()

ipdaress = socket.gethostbyname(os.environ['ISF_MASTER_NAME']).replace('100','102')

f.write('{}\n'.format(ipdaress))
f.flush()

# parse keyword arguments
class StoreDictKeyPair(argparse.Action):
    """https://stackoverflow.com/questions/29986185/python-argparse-dict-arg
    parsing command-line arguments as a dictionary with argparse
    used for notebook run kwargs (not yet implemented in submit.sh or setup_SLURM)

    """

    def __call__(self, parser, namespace, values, option_string=None):
        my_dict = {}
        for kv in values.split(","):
            k, v = kv.split("=")
            my_dict[k] = v
        setattr(namespace, self.dest, my_dict)

parser = argparse.ArgumentParser()
parser.add_argument('notebook_name') # compulsory argument
parser.add_argument("nb_kwargs_from_command_line", action=StoreDictKeyPair, metavar="KEY1=VAL1,KEY2=VAL2...", nargs='?', const=None)
arguments = parser.parse_args()
notebook_kwargs = arguments.nb_kwargs_from_command_line
notebook_path = arguments.notebook_name
f.write('{}_{}\n'.format(notebook_path,notebook_kwargs))
f.flush()

# setup dask, locking, ...
now = datetime.today()
management_dir = 'batch_{}'.format(os.environ['SLURM_JOBID'])
f.write('{}\n'.format(management_dir))
f.flush()


setup_SLURM.main(management_dir,
                 launch_jupyter_server=True,
                 sleep = False)

f.write('done with SLURM setup\n')
f.flush()

client = distributed.Client('{}:{}'.format(ipdaress, port)) # get_client()
waiting_for = int(os.environ['SLURM_CPUS_PER_TASK']) * int(os.environ['SLURM_NPROCS'])
f.write('waiting for {} workers'.format(waiting_for))
f.flush()
client.wait_for_workers()
f.write('all workers there')
f.flush()

event_done = distributed.Event('done')  

if os.environ['SLURM_PROCID'] == '0':
    suffix = ['{}_{}'.format(k,v) for k,v in notebook_kwargs.items()]
    suffix = '__'.join(suffix)
    os.makedirs(notebook_path, exist_ok=True)
    run_notebook(notebook_path, 
                 nb_kwargs = notebook_kwargs, 
                 out_path = '.',
                 nb_suffix = '_' + suffix,
                 timeout = 3600*24*365*100)    
    event_done.set()
else:
    event_done.wait(timeout = 3600*24*365*100)