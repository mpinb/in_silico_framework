"""The main file to run a complete setup when submitting a SLURM job

Depending on your needs, it sets up the following things on your requested resources:
On process 0:
    1. The locking server
    2. The dask scheduler, and dask workers
    3. The jupyter server

On all other processes:
    1. Reads and respects the locking configuration setup by process 0
    2. Sets up dask workers that communicate with the dask scheduler on process 0
"""

# coding: utf-8

import fasteners
import os
import sys
import time
import configparser
from SLURM_scripts.setup_locking_server import setup_locking_server, setup_locking_config
from SLURM_scripts.setup_dask_workers import setup_dask_scheduler, setup_dask_workers
from SLURM_scripts.setup_jupyter_server import setup_jupyter_server
from contextlib import contextmanager
import argparse
from SLURM_scripts.nbrun import run_notebook
from socket import gethostbyname, gethostname


class StoreDictKeyPair(argparse.Action):
    """https://stackoverflow.com/questions/29986185/python-argparse-dict-arg
    parsing command-line arguments as a dictionary with argparse
    used for notebook run kwargs (not yet implemented in submit.sh or setup_SLURM)

    """

    def __call__(self, parser, namespace, values, option_string=None):
        my_dict = {}
        for kv in values.split(","):
            k, v = kv.split("=")
            my_dict[k] = eval(v)
        setattr(namespace, self.dest, my_dict)


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
        p = lock.path  # this is a regular string in Python 2
        if type(p) == bytes:  # Python 3 returns a byte string as lock.path
            p = p.decode("utf-8")
        p += '_sync'
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

# def get_process_number(management_dir):
#     return int(os.environ['SLURM_PROCID'])

def reset_process_number(management_dir):
    with Lock(management_dir) as lock:
        p = lock.path  # this is a regular string in Python 2
        if type(p) == bytes:  # Python 3 returns a byte string as lock.path
            p = p.decode("utf-8")
        p += '_sync'
        with open(p, 'w') as f:
            f.write('')


def read_user_port_numbers():
    ### setting up user-defined port numbers ###
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))
    config = configparser.ConfigParser()
    config.read(os.path.join(__location__, 'user_settings.ini'))
    ports = config['PORT_NUMBERS']
    return ports


def main(management_dir,
         launch_jupyter_server=True,
         notebook=None,
         nb_kwargs=None,
         sleep = True):
    if not os.path.exists(management_dir):
        try:
            print('creating management dir')
            os.makedirs(management_dir)
        except OSError:  # if another process was faster creating it
            pass
    PROCESS_NUMBER = get_process_number(management_dir)
    PORTS = read_user_port_numbers()

    if PROCESS_NUMBER == 0:
        setup_locking_server(management_dir, PORTS)
        setup_dask_scheduler(
            management_dir,
            PORTS)  # this process creates scheduler.json and scheduler3.json
        if launch_jupyter_server:
            setup_jupyter_server(management_dir, PORTS)
        # Set the IP adress of whatever node you got assigned as a environment variable
    # TODO: why doesn't this work? It does not seem to be added to the environment variables
    ip = gethostbyname(
        gethostname()
    )  # fetches the ip of the current host, usually "somnalogin01" or "somalogin02"
    os.environ['IP_MAIN'] = ip
    os.environ['IP_INFINIBAND'] = ip.replace(
        '100', '102')  # a bit hackish, but it works

    setup_locking_config(management_dir)
    setup_dask_workers(management_dir)

    if notebook is not None and PROCESS_NUMBER == 0:
        run_notebook(notebook, nb_kwargs=nb_kwargs)
        exit(0)  # quit SLURM when notebook has finished running
    else:
        if sleep:
            time.sleep(60 * 60 * 24 * 365)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('management_dir')  # non-optional positional argument
    parser.add_argument("--nb_kwargs", dest="nb_kwargs_from_cline", action=StoreDictKeyPair, metavar="KEY1=VAL1,KEY2=VAL2...", nargs='?', const=None)
    # parser.add_argument("--nb_suffix", nargs='?', const="-out", default="-out")
    parser.add_argument("--launch_jupyter_server",
                        default=True,
                        action='store_true')
    parser.add_argument('--notebook_name', nargs='?', const="", default=None)
    args = parser.parse_args()

    MANAGEMENT_DIR = args.management_dir
    LAUNCH_JUPYTER_SERVER = args.launch_jupyter_server  # False by default, if left unspecified

    if LAUNCH_JUPYTER_SERVER:
        print("Launching Jupyter server: {}".format(LAUNCH_JUPYTER_SERVER))
    print('using management dir {}'.format(MANAGEMENT_DIR))

    if args.notebook_name is not None:
        print("Running notebook {}".format(args.notebook_name))
        print("with kwargs {}".format(args.nb_kwargs_from_cline))

    main(
        MANAGEMENT_DIR,
        LAUNCH_JUPYTER_SERVER,
        notebook=args.notebook_name,
        nb_kwargs=args.nb_kwargs_from_cline
    )

    