import os


#################################################
# setting up dask-scheduler
#################################################
def _get_sfile(management_dir):
    return os.path.join(management_dir,
                        'scheduler.json'), os.path.join(management_dir,
                                                        'scheduler3.json')


def setup_dask_scheduler(management_dir, ports):
    """Set up dask scheduler
    This process is normally exectuted by only one thread on the cluster.
    It keeps track of all the dask workers, distributes tasks and fetches results.

    Args:
        management_dir (str): location of the management dir
        ports (dict | dict-like): A dictionary of port numbers to use for the dask setup.
            Must containg the following keys: 'dask_client_2', 'dask_dashboard_2', 'dask_client_3' and 'dask_dashboard_3'
            Each key must have a port number as value.
            Should be specified in ./user_settings.ini
    """
    from distributed.versions import get_versions
    print("versions:\n", get_versions())
    print('-' * 50)
    print('setting up dask-scheduler')
    sfile, sfile3 = _get_sfile(management_dir)
    command = 'dask-scheduler --scheduler-file={} --port={} --bokeh-port={} --interface=ib0 &'
    command = command.format(sfile, ports['dask_client_2'],
                             ports['dask_dashboard_2'])
    print(command)
    os.system(command)
    command = '''bash -ci "source ~/.bashrc; source_3; dask-scheduler --scheduler-file={} --port={} --interface=ib0 --dashboard-address=:{}" &'''
    command = command.format(sfile3, ports['dask_client_3'],
                             ports['dask_dashboard_3'])
    print(command)
    os.system(command)
    print('-' * 50)


#################################################
# setting up dask-worker
#################################################
def setup_dask_workers(management_dir):
    """Set up dask workers.
    This process is done by all threads normally (even process 0).
    It sets up dask workers which receive tasks, compute them, and send the result to the dask scheduler.

    Args:
        management_dir (str): The location of the management dir
    """
    print('-' * 50)
    print('setting up dask-workers')
    n_cpus = os.environ['SLURM_CPUS_PER_TASK']
    sfile, sfile3 = _get_sfile(management_dir)
    command = 'dask-worker --nthreads 1  --nprocs {nprocs} --scheduler-file={sfile} --memory-limit=100e9 --local-directory $JOB_TMPDIR &'.format(
        nprocs=n_cpus, sfile=sfile)
    print(command)
    os.system(command)
    command = '''bash -ci "source ~/.bashrc; source_3; dask-worker --nthreads 1  --nprocs {nprocs} --scheduler-file={sfile} --local-directory $JOB_TMPDIR --memory-limit=100e9" &'''
    command = command.format(nprocs=n_cpus, sfile=sfile3)
    print(command)
    os.system(command)
    print('-' * 50)
