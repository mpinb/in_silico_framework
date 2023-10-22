# coding: utf-8

# In[1]:

import fasteners
import os
import shutil
import sys
import yaml
import socket
import time

#################################
# methods for coordinating jobs
#################################

from contextlib import contextmanager


@contextmanager
def Lock(management_dir):
    # Code to acquire resource, e.g.:
    lock = fasteners.InterProcessLock(os.path.join(management_dir, 'lock'))
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()


def get_process_number(management_dir):
    with Lock(management_dir) as lock:
        p = lock.path + '_sync'
        if not os.path.exists(p):
            with open(p, 'w') as f:
                pass
        with open(p, 'r') as f:
            x = f.read()
            if x == '':
                x = 0
            else:
                x = int(x)
        with open(p, 'w') as f:
            f.write(str(x + 1))
        print('I am process number {}'.format(x))
    return x


def reset_process_number():
    with Lock() as lock:
        with open(lock.path + '_sync', 'w') as f:
            f.write('')


# In[5]:


#################################################
# setting up locking server
#################################################
def get_locking_file_path():
    return os.path.join(management_dir, 'locking_server')


def setup_locking_server():
    print('-' * 50)
    print('setting up locking server')
    #command = 'redis-server --save "" --appendonly no --port 8885 --protected-mode no &'
    #print command
    #os.system(command)
    config = [
        dict(type='redis',
             config=dict(host=socket.gethostname(), port=8885,
                         socket_timeout=1))
    ]
    config = [{'config': {'hosts': 'axon01:21811'}, 'type': 'zookeeper'}]
    with open(get_locking_file_path(), 'w') as f:
        f.write(yaml.dump(config))
    setup_locking_config()
    print('-' * 50)


def setup_locking_config():
    print('-' * 50)
    print('updating locking configuration to use new server')
    while not os.path.exists(get_locking_file_path()):
        time.sleep(1)
    os.environ['ISF_DISTRIBUTED_LOCK_CONFIG'] = get_locking_file_path()
    check_locking_config()
    print('-' * 50)


def check_locking_config():
    import model_data_base.distributed_lock
    print('locking configuration')
    print(model_data_base.distributed_lock.server)
    print(model_data_base.distributed_lock.client)
    #assert model_data_base.distributed_lock.server['type'] == 'redis'
    #import socket
    #socket.gethostname()

    #config = [dict(type = 'redis', config = dict(host = socket.gethostname(), port = 8885, socket_timeout = 1))]

    #print 'old locking configuration'
    #print model_data_base.distributed_lock.server
    #print model_data_base.distributed_lock.client

    #import time
    #while True:
    #    try:
    #        model_data_base.distributed_lock.update_config(config)
    #        break
    #    except RuntimeError:
    #        print 'could not connect, retrying in 1 sec'
    #        time.sleep(1)

    #print 'updated locking configuration'
    #print model_data_base.distributed_lock.server
    #print model_data_base.distributed_lock.client


# In[6]:


#################################################
# setting up dask-scheduler
#################################################
def _get_sfile(management_dir):
    return os.path.join(management_dir,
                        'scheduler.json'), os.path.join(management_dir,
                                                        'scheduler3.json')


def setup_dask_scheduler(management_dir):
    print('-' * 50)
    print('setting up dask-scheduler')
    sfile, sfile3 = _get_sfile(management_dir)
    command = 'dask-scheduler --scheduler-file={} --port=28786 --bokeh-port=28787 &'
    command = command.format(sfile)
    print(command)
    os.system(command)
    command = '''bash -ci "source ~/.bashrc; source_3; dask-scheduler --scheduler-file={} --port=38786 --dashboard-address=:38787" &'''
    command = command.format(sfile3)
    print(command)
    os.system(command)
    print('-' * 50)


# In[7]:


#################################################
# setting up dask-worker
#################################################
def setup_dask_workers(management_dir):
    print('-' * 50)
    print('setting up dask-workers')
    import psutil
    n_cpus = psutil.cpu_count(logical=False)
    sfile, sfile3 = _get_sfile(management_dir)
    command = 'dask-worker --nthreads 1  --nprocs {nprocs} --scheduler-file={sfile} --memory-limit=100e9 &'.format(
        nprocs=n_cpus, sfile=sfile)
    print(command)
    os.system(command)
    command = '''bash -ci "source ~/.bashrc; source_3; dask-worker --nthreads 1  --nprocs {nprocs} --scheduler-file={sfile} --memory-limit=100e9" &'''
    command = command.format(nprocs=n_cpus, sfile=sfile3)
    print(command)
    os.system(command)
    print('-' * 50)


##############################################
# setting up jupyter-notebook
#############################################
def setup_jupyter_notebook():
    print('-' * 50)
    print('setting up jupyter notebook')
    check_locking_config()
    command = "cd notebooks; jupyter-notebook --ip='*' --no-browser --port=11112 &"
    print(command)
    os.system(command)
    print('-' * 50)
    #command = "conda activate /axon/scratch/abast/anaconda3/; jupyter-lab --ip='*' --no-browser --port=11113 &"
    #command = 'screen -S jupyterlab -dm bash -c "source ~/.bashrc; source_3; ' +     '''jupyter-lab --ip='*' --no-browser --port=11113"'''
    #command = '''bash -c "source ~/.bashrc; source_3; jupyter-lab --ip='*' --no-browser --port=11113" &'''
    #command = '''(source ~/.bashrc; source_3; jupyter-lab --ip='*' --no-browser --port=11113) &'''
    command = '''bash -ci "source ~/.bashrc; source_3; jupyter-lab --ip='*' --no-browser --port=11113 --NotebookApp.token='' --NotebookApp.password=''" &'''
    #command = "/axon/scratch/abast/anaconda3/bin/jupyter-lab --ip='*' --no-browser --port=11113"
    os.system(command)


# In[8]:
if __name__ == "__main__":
    try:
        management_dir = sys.argv[1]
    except IndexError:
        sys.exit(1)
    print('using management dir ' + str(management_dir))

    #if os.path.exists(management_dir):
    #    shutil.rmtree(management_dir)
    if not os.path.exists(management_dir):
        try:
            os.makedirs(management_dir)
        except OSError:  # if another process was faster creating it
            pass

    process_number = get_process_number(management_dir)
    if process_number == 0:
        setup_locking_server()
        setup_dask_scheduler(management_dir)
        # setup_jupyter_notebook()
    setup_locking_config()
    setup_dask_workers(management_dir)
    if process_number == 0:
        setup_jupyter_notebook()
    time.sleep(60 * 60 * 24 * 365)
