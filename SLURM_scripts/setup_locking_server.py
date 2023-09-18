import os
import yaml
import time

#################################################
# setting up locking server
#################################################
def get_locking_file_path(management_dir):
    return os.path.join(management_dir, 'locking_server')

def setup_locking_server(management_dir, ports):
    """Set up locking server
    This process is normally exectuted by only one thread on the cluster.
    
    The locking server keeps track of all write and read operations. It makes sure that no two processes
    write to the same location in memory (which would lead to a corrupted file, or worse).

    Args:
        ports (dict | dict-like): A dictionary of port numbers to use for the dask setup.
            Must containg the following keys: 'dask_client_2', 'dask_dashboard_2', 'dask_client_3' and 'dask_dashboard_3'
            Each key must have a port number as value.
            Should be specified in ./user_settings.ini
    
    """
    print('-'*50)
    print('setting up locking server')
    #command = 'redis-server --save "" --appendonly no --port 8885 --protected-mode no &'    
    #print command
    #os.system(command)
    #config = [dict(type = 'redis', config = dict(host = socket.gethostname(), port = 8885, socket_timeout = 1))]
    config = [{
        'config': {
            'hosts': 'somalogin02-hs:{}'.format(ports['locking_server'])
            }, 
        'type': 'zookeeper'}]
    # config = [{'type': 'file'}]  # uncomment this line if zookeeper is not running (i.e., you receive an error similar to 'No handlers could be found for logger "kazoo.client"')
    with open(get_locking_file_path(management_dir), 'w') as f:
        f.write(yaml.dump(config))
    setup_locking_config(management_dir)
    print('-'*50)

def setup_locking_config(management_dir):
    print('-'*50)
    print('updating locking configuration to use new server')
    while not os.path.exists(get_locking_file_path(management_dir)):
        time.sleep(1)
    os.environ['ISF_DISTRIBUTED_LOCK_CONFIG'] = get_locking_file_path(management_dir) 
    check_locking_config()
    print('-'*50)

def check_locking_config():
    import model_data_base.distributed_lock
    print('locking configuration')
    print(model_data_base.distributed_lock.server)
    print(model_data_base.distributed_lock.client)
    #assert(model_data_base.distributed_lock.server['type'] == 'redis')
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

if __name__ == "__main__":
    import argparse
    from setup_SLURM import get_process_number, read_user_port_numbers
    parser = argparse.ArgumentParser()
    parser.add_argument('management_dir')  # non-optional positional argument
    # parser.add_argument("--nb_kwargs", dest="nb_kwargs_from_cline", action=StoreDictKeyPair, metavar="KEY1=VAL1,KEY2=VAL2...", nargs='?', const=None)
    # parser.add_argument("--nb_suffix", nargs='?', const="-out", default="-out")
    parser.add_argument("--launch_jupyter_server", default=True, action='store_true')
    parser.add_argument('--notebook_name', nargs='?', const="", default=None)
    args = parser.parse_args()

    MANAGEMENT_DIR = args.management_dir
    if not os.path.exists(MANAGEMENT_DIR):
        try:    
            os.makedirs(MANAGEMENT_DIR)
        except OSError: # if another process was faster creating it
            pass
    PROCESS_NUMBER = get_process_number(MANAGEMENT_DIR)
    PORTS = read_user_port_numbers()

    setup_locking_server(MANAGEMENT_DIR, PORTS)