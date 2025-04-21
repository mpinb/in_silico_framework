"""
This file provides methods and configurations to for servers that do not provide SLURM job managing.
With these methods, it is still possible to set up DASK workers and monitor them, and exectute terminal commands on remote machines from within python.

Author: unknown

Last updated: 23/01/2023 by Bjorge Meulemeester
"""

import os
from distutils.version import LooseVersion, StrictVersion
import warnings


def run_command_remotely(server,
                         command,
                         print_command=True,
                         print_output=True):
    command = '''ssh -tt {} << 'ENDSSH' \n {} \n exit \n ENDSSH'''.format(
        server, command)
    if print_command:
        print(command)
    out = os.popen(command).read()
    if print_output:
        print(out)


def list_all_screens():
    for server in {'katz', 'nernst', 'rall', 'cajal', 'hodgkin', 'golgi'}:
        run_command_remotely(server, 'screen -ls', print_command=False)


# def start_cluster(servers = 'all', nice = 8, nprocs_update = {}, tmpdir = '/tmp/abast', scheduler = 'rall', suffix = ''):
#     ip_lookup = {'katz': '22', 'nernst': '21', 'rall': '20', 'cajal': '26', 'golgi': '23', 'hodgkin': '25', 'spock': '12', 'riker': '13'}
#
#     n_procs = {'katz': 40, 'nernst': 35, 'rall': 40, 'cajal': 24, 'golgi': 24, 'hodgkin': 24, 'spock': 4, 'riker': 4}
#     n_procs.update(nprocs_update)
#
#     if servers == 'all': servers = n_procs.keys()
#     elif servers == 'new': servers = ['rall', 'nernst', 'katz']
#     elif servers == 'old': servers = ['cajal', 'golgi', 'hodgkin']
#
#     print 'starting scheduler'
#     command = 'source_isf; screen -S scheduler_{suffix} -dm bash -c "dask-scheduler"'.format(suffix = suffix)
#     run_command_remotely(scheduler, command)
#
#     print 'starting workers'
#     template = 'source_isf; screen -S workers_{suffix} -dm bash -c "nice -n {nice} dask-worker --nthreads 1  --nprocs {nprocs} {ip}:8786 --local-directory {tmpdir} --memory-limit=100e9"'
#     for server in servers:
#         command = template.format(suffix = suffix, nice = nice, nprocs = n_procs[server], ip = '10.40.130.'+ip_lookup[scheduler], tmpdir = tmpdir)
#         run_command_remotely(server, command)


def start_cluster(servers='all',
                  nice=8,
                  nprocs_update={},
                  tmpdir='/tmp/abast',
                  scheduler='rall',
                  suffix='',
                  port=8786):
    ip_lookup = {
        'katz': '22',
        'nernst': '21',
        'rall': '20',
        'cajal': '26',
        'ibs3005': '27',
        'golgi': '23',
        'hodgkin': '25',
        'spock': '12',
        'riker': '13'
    }

    n_procs = {
        'katz': 40,
        'nernst': 35,
        'rall': 40,
        'cajal': 24,
        'golgi': 24,
        'hodgkin': 24,
        'spock': 4,
        'riker': 4,
        'ibs3005': 18
    }
    n_procs.update(nprocs_update)

    if servers == 'all':
        servers = ['rall', 'nernst', 'katz'] + ['rall', 'nernst', 'katz']
    elif servers == 'new':
        servers = ['rall', 'nernst', 'katz']
    elif servers == 'old':
        servers = ['cajal', 'golgi', 'hodgkin']

    print('starting scheduler')
    command = 'source /nas1/Data_arco/.bashrc; source_isf; screen -S scheduler_{suffix} -dm bash -c "source /nas1/Data_arco/.bashrc; source_isf; dask-scheduler --port {port} --bokeh-port {bokeh_port}"'.format(
        suffix=suffix, port=str(port), bokeh_port=str(port + 1))
    run_command_remotely(scheduler, command)

    print('starting workers')
    template = 'source /nas1/Data_arco/.bashrc; source_isf; screen -S workers_{suffix} -dm bash -c "source /nas1/Data_arco/.bashrc \n source_isf; nice -n {nice} dask-worker --nthreads 1  --nprocs {nprocs} {ip}:{port} --local-directory {tmpdir} --memory-limit=100e9"'
    for server in servers:
        command = template.format(suffix=suffix,
                                  nice=nice,
                                  nprocs=n_procs[server],
                                  ip='10.40.130.' + ip_lookup[scheduler],
                                  port=port,
                                  tmpdir=tmpdir)
        run_command_remotely(server, command)


import cloudpickle


def cache(function):
    from six.moves import cPickle
    import hashlib
    memo = {}

    def get_key(*args, **kwargs):
        try:
            hash = hashlib.md5(cPickle.dumps([args, kwargs])).hexdigest()
        except TypeError:
            hash = hashlib.md5(cloudpickle.dumps([args, kwargs])).hexdigest()
        return hash

    def wrapper(*args, **kwargs):
        key = get_key(*args, **kwargs)
        if key in memo:
            return memo[key]
        else:
            rv = function(*args, **kwargs)
            memo[key] = rv
            return rv

    return wrapper


try:
    import distributed

    @cache
    def cluster(*args, **kwargs):
        c = distributed.Client(*args, **kwargs)

        # import matplotlib to avoid error with missing Qt backend
        def fun():
            import matplotlib
            matplotlib.use('Agg')

        c.run(fun)

        # switch off work stealing, otherwise, simulations may run twice
        # update: work stealing is now transactional, see
        # https://github.com/dask/distributed/commit/efb7f1ab3c14d6b2ca15dcd04ca1c2b226cc7cbb
        # Until this commit is provided through the conda channels, we switch work stealing off completely
        if LooseVersion(distributed.__version__) < LooseVersion('1.20.0'):
            warnings.warn("Your version of distributed seems to be < '1.20.0'. Work stealing is " +
                          "therefore not transactional. This means, that simulations might run " +
                          "more than once in an unpredictable manner. To ensure that " + \
                          "simulations do not run twice, work stealing is switched of now. " + \
                          "However, this will have a negative impact on work balancing on the scheduler. " + \
                          "Please update distributed to a version >= 1.20.0.")
            #def switch_of_work_stealing(dask_scheduler=None):
            #    dask_scheduler.extensions['stealing']._pc.stop()
            #c.run_on_scheduler(switch_of_work_stealing)
        return c

    print("setting up local multiprocessing framework ... done")
except ImportError:
    pass
