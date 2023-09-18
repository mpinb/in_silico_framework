import six
import distributed
import os

def get_user_port_numbers():
    """Read the port numbers defined in SLURM_scripts/user_settings.ini

    Returns:
        dict: port numbers as values, names as keys
    """
    import configparser
    # user-defined port numbers
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
    config = configparser.ConfigParser()
    config.read(os.path.join(__location__, 'user_settings.ini'))
    ports = config['PORT_NUMBERS']
    return ports

def get_client():
    """Gets the distributed.client object if dask has been setup

    Returns:
        Client: the client object
    """
    ports = get_user_port_numbers()
    if six.PY2:
        client_port = ports['dask_client_2']
    else:
        client_port = ports['dask_client_3']

    from socket import gethostbyname, gethostname
    hostname = gethostname()
    ip = gethostbyname(hostname)  # fetches the ip of the current host, usually "somnalogin01" or "somalogin02"
    if 'soma' in hostname:
        #we're on the soma cluster and have infiniband
        ip_infiniband = ip.replace('100', '102')  # a bit hackish, but it works
        client = distributed.Client(ip_infiniband+':'+client_port)
    else:
        client = distributed.Client(ip+':'+client_port)
    return client
