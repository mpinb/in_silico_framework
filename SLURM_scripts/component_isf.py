from __future__ import print_function
from curses.ascii import isdigit

import os
import sys
import six
import yaml
import time
import psutil
import logging
import fasteners

#NOTE: For this import to succeed the in_silico_framework
#      source folders needs to be added to the PYTHONPATH
import model_data_base.distributed_lock as mdb_dist_lock

#NOTE: logging level currently set to INFO
#change to DEBUG to see actual OS commands
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setStream(sys.stdout)
logger.addHandler(handler)

#The script has a second parameter to launch jupyter
#using a port number defined by the user via slurm script
if isinstance(sys.argv[2], int):
    jupyter_port = sys.argv[2]
elif six.PY2:
    jupyter_port = '11118'
else:
    jupyter_port = '11119'

#NOTE: management dir being passed as a command line
#argument. If missing a random generated name is used
if sys.argv[1]:
    management_dir = sys.argv[1]
else:
    slurm_job_id = os.environ['SLURM_JOB_ID']
    management_dir = 'conf_dir_{}'.format(slurm_job_id)

logger.info('using management dir {}'.format(management_dir))

if not os.path.exists(management_dir):
    try:
        os.makedirs(management_dir)
    except OSError:  # if another process was faster creating it
        pass

#NOTE: last bit of information is to use the hostname
#to determine in which cluster the script is running.
hostname = os.environ['HOSTNAME']
cluster = hostname[:4]
logger.info('script executing in {}'.format(cluster))

#################################
# locking servers
#################################
lock_server = {'axon': 'axon01:21811', 'soma': 'somalogin01-hs:33333'}

#################################
# methods for coordinating jobs
#################################

from contextlib import contextmanager


@contextmanager
def Lock():
    # Code to acquire resource, e.g.:
    lock = fasteners.InterProcessLock(os.path.join(management_dir, 'lock'))
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()


def get_process_number():
    with Lock() as lock:
        p = lock.path + b'_sync'
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
        logger.info('I am process number {}'.format(x))
    return x


def reset_process_number():
    with Lock() as lock:
        p = lock.path + b'_sync'
        with open(p, 'w') as f:
            f.write('')


process_number = get_process_number()


#################################################
# setting up locking server
#################################################
def get_locking_file_path():
    return os.path.join(management_dir, 'locking_server')


def setup_locking_server(cluster):
    logger.info('setting up locking server')
    #command = 'redis-server --save "" --appendonly no --port 8885 --protected-mode no &'
    #config = [dict(type = 'redis', config = dict(host = socket.gethostname(), port = 8885, socket_timeout = 1))]
    #config = [{'config': {'host': socket.gethostname(), 'port': 8885, 'socket_timeout': 1}, 'type': 'redis'}]
    config = [{'config': {'hosts': lock_server[cluster]}, 'type': 'zookeeper'}]
    with open(get_locking_file_path(), 'w') as f:
        f.write(yaml.dump(config))


def setup_locking_config():
    logger.info('updating locking configuration to use new server')
    while not os.path.exists(get_locking_file_path()):
        time.sleep(1)
    os.environ['ISF_DISTRIBUTED_LOCK_CONFIG'] = get_locking_file_path()
    check_locking_config()


def check_locking_config():
    logger.info('locking configuration')
    logger.info('distributed lock server: {}'.format(mdb_dist_lock.server))
    logger.info('distributed lock client: {}'.format(mdb_dist_lock.client))


#################################################
# setting up dask-scheduler
#################################################
def _get_sfile(management_dir):
    return os.path.join(management_dir,
                        'scheduler.json'), os.path.join(management_dir,
                                                        'scheduler3.json')


def setup_dask_scheduler(management_dir):
    logger.info('setting up dask-scheduler')
    sfile, sfile3 = _get_sfile(management_dir)

    if six.PY2:
        command = 'dask-scheduler --scheduler-file={} --port=28786 --bokeh-port=28787 &'
        command = command.format(sfile)
    else:  # assume we are using python3
        command = 'dask-scheduler --scheduler-file={} --port=38786 --dashboard-address=38787 &'
        command = command.format(sfile3)

    logger.debug(command)
    os.system(command)


#################################################
# setting up dask-workers
#################################################
def setup_dask_workers(management_dir):
    logger.info('setting up dask-workers')
    n_cpus = psutil.cpu_count(logical=False)  # maybe one less
    sfile, sfile3 = _get_sfile(management_dir)

    if six.PY2:
        command = 'dask-worker --nthreads 1  --nprocs {nprocs} --scheduler-file={sfile} --memory-limit=100e9 &'
        command = command.format(nprocs=n_cpus, sfile=sfile)
    else:  # assume we are using python3
        command = 'dask-worker --nthreads 1  --nprocs {nprocs} --scheduler-file={sfile} --memory-limit=100e9 &'
        #command = "dask-worker --nworkers='auto' --memory-limit='auto' --scheduler-file={sfile} &"
        command = command.format(nprocs=n_cpus, sfile=sfile3)
        #command = command.format(sfile = sfile3)

    logger.debug(command)
    os.system(command)


##############################################
# setting up jupyter-notebook
#############################################
def setup_jupyter_notebook(custom_port):
    logger.info("setting up jupyter notebook ({}) ".format(custom_port))
    check_locking_config()

    if six.PY2:
        command = "jupyter-notebook --ip='*' --no-browser --port={port}"
        command = command.format(port=custom_port)
    else:
        #command = "jupyter-lab --ip='*' --no-browser --port={port} --NotebookApp.token='' --NotebookApp.password=''"
        command = "jupyter-lab --no-browser --port={port}"
        command = command.format(port=custom_port)

    logger.debug(command)
    os.system(command)


if __name__ == "__main__":
    if process_number == 0:
        setup_locking_server(cluster)
        setup_locking_config()
        setup_dask_scheduler(management_dir)
        setup_dask_workers(management_dir)
        setup_jupyter_notebook(jupyter_port)
    else:
        setup_locking_config()
        setup_dask_workers(management_dir)
