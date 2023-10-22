## init
dask2slrm_TEMPLATE = '''#!/bin/bash

# Example of running python script with a job array

#SBATCH -J dsk2slrm
#SBATCH -p CPU,GPU
#SBATCH --array=1-{}                    # how many tasks in the array
#SBATCH -c 1                            # one CPU core per task
#SBATCH -t 24:00:00
#SBATCH -o run-%j-%a.out
#SBATCH -e run-%j-%a.err
#SBATCH --mem=8000
#SBATCH --output=none
#SBATCH --error=none

# Run python script with a command line argument
srun {} run.py $SLURM_ARRAY_TASK_ID 
'''

runpy_TEMPLATE = '''import os
import sys
import cloudpickle
import dask
path = '{}'
n_folders = {}
id_ = int(sys.argv[1])
basedir = os.path.basename(path)
subdir = str((id_ - 1) % n_folders)
path_to_delayed = os.path.join(path, subdir, str(id_))
if os.path.exists(path_to_delayed + '.done'):
    exit()
with open(path_to_delayed, 'rb') as f:
    d = cloudpickle.load(f)
dask.compute(d, scheduler = 'synchronous')
os.rename(path_to_delayed, path_to_delayed+'.done')'''
import numpy as np
import os
import sys
import cloudpickle


def convertible_to_int(x):
    try:
        int(x)
        return True
    except:
        return False


def save_delayeds_in_folder(folder_, ds, files_per_folder=100):
    n_folders = int(np.ceil(len(ds) / files_per_folder))
    for lv, d in enumerate(ds):
        subdir = str(lv % n_folders)
        if not os.path.exists(folder_.join(subdir)):
            os.makedirs(folder_.join(subdir))
        with open(folder_.join(subdir).join(str(lv + 1)), 'wb') as f:
            cloudpickle.dump(d, f)
    with open(folder_.join('slurm.sh'), 'w') as f:
        f.write(dask2slrm_TEMPLATE.format(len(ds) + 1, sys.executable))
    with open(folder_.join('run.py'), 'w') as f:
        f.write(runpy_TEMPLATE.format(folder_, n_folders))


def check_all_done(folder_):
    subdirs = [f for f in os.listdir(folder_) if convertible_to_int(f)]
    for s in subdirs:
        full_path = os.path.join(folder_, s)
        ds = os.listdir(full_path)
        for d in ds:
            if not d.endswith('.done'):
                print(s, d)
