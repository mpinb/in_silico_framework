import os
from SLURM_scripts.setup_locking_server import check_locking_config


##############################################
# setting up jupyter-notebook
#############################################
def setup_jupyter_server(management_dir, ports):
    """Sets up the jupyter server for both jupyter notebook and jupyter lab
    This process is normally exectuted by only one thread on the cluster.

    Args:
        management_dir (str): location of the management dir
        ports (dict | dict-like): A dictionary of port numbers to use for the dask setup.
            Must containg the following keys: 'dask_client_2', 'dask_dashboard_2', 'dask_client_3' and 'dask_dashboard_3'
            Each key must have a port number as value.
            Should be specified in ./user_settings.ini
    """
    print('-' * 50)
    print('setting up jupyter notebook')
    check_locking_config()

    ##### Setup server for Jupyter notebook #####
    command = "cd notebooks; jupyter-notebook --ip='*' --no-browser --port={} "
    command = command.format(ports['jupyter_notebook'])
    print(command)
    # Redirect both stdout and stderr (&) to file
    os.system(command +
              "&>>{} &".format(os.path.join(management_dir, "jupyter.txt")))
    print('-' * 50)

    ##### Setup server for Jupyter Lab #####
    #command = "conda activate /axon/scratch/abast/anaconda3/; jupyter-lab --ip='*' --no-browser --port=11113 &"
    #command = 'screen -S jupyterlab -dm bash -c "source ~/.bashrc; source_3; ' +     '''jupyter-lab --ip='*' --no-browser --port=11113"'''
    #command = '''bash -c "source ~/.bashrc; source_3; jupyter-lab --ip='*' --no-browser --port=11113" &'''
    #command = '''(source ~/.bashrc; source_3; jupyter-lab --ip='*' --no-browser --port=11113) &'''
    command = '''bash -ci "source ~/.bashrc; source_3; jupyter-lab --ip='*' --no-browser --port={} --NotebookApp.allow_origin='*' " '''
    command = command.format(ports['jupyter_lab'])
    #command = "/axon/scratch/abast/anaconda3/bin/jupyter-lab --ip='*' --no-browser --port=11113"
    # append output to same file as notebook (ance the >> operator rather than >)
    os.system(command +
              "&>>{} &".format(os.path.join(management_dir, "jupyter.txt")))


if __name__ == "__main__":
    import argparse
    from setup_SLURM import get_process_number, read_user_port_numbers
    parser = argparse.ArgumentParser()
    parser.add_argument('management_dir')  # non-optional positional argument
    # parser.add_argument("--nb_kwargs", dest="nb_kwargs_from_cline", action=StoreDictKeyPair, metavar="KEY1=VAL1,KEY2=VAL2...", nargs='?', const=None)
    # parser.add_argument("--nb_suffix", nargs='?', const="-out", default="-out")
    parser.add_argument("--launch_jupyter_server",
                        default=True,
                        action='store_true')
    parser.add_argument('--notebook_name', nargs='?', const="", default=None)
    args = parser.parse_args()

    MANAGEMENT_DIR = args.management_dir
    if not os.path.exists(MANAGEMENT_DIR):
        try:
            os.makedirs(MANAGEMENT_DIR)
        except OSError:  # if another process was faster creating it
            pass
    PROCESS_NUMBER = get_process_number(MANAGEMENT_DIR)
    PORTS = read_user_port_numbers()

    setup_jupyter_server(MANAGEMENT_DIR, PORTS)