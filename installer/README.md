# How to setup In-Silico-Framework

**Contents**

1. [Requirements](#requirements)
2. [Bash Profile Setup](#setup)
3. [Folder Structure](#structure)
4. [Clone In-Silico-Framework](#repository)
5. [Install In-Silico-Framework](#install)
6. [IPython Kernels](#kernels)
7. [Test Submit Jobs](#testing)
8. [Default Ports](#ports)
9. [Jupyter Extensions](#extensions)
10. [Other Config](#other-config)
11. [References](#references)

## Requirements

Every student needs to be able to synchronize their repository with https://github.com/research-center-caesar/in_silico_framework


## Setup

Insert this lines into bash_profile, e.g. by using `vim ~/.bashrc`
Note: adapt the path mybasedir path for your cluster:

```bash
shopt -s expand_aliases
export MYBASEDIR="/gpfs/soma_fs/scratch/$USER"
module load git/2.31
ulimit -Sn "$(ulimit -Hn)"
export PYTHONPATH=$MYBASEDIR/project_src/in_silico_framework
export ISF_HOME=$MYBASEDIR/project_src/in_silico_framework
alias source_isf='source $MYBASEDIR/anaconda_isf2/bin/activate; export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH; cd $MYBASEDIR'
alias source_3='source $MYBASEDIR/anaconda_isf3/bin/activate; export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH; cd $MYBASEDIR'
alias isf='cd $ISF_HOME'
alias wip='cd $MYBASEDIR/notebooks'
alias data='cd $MYBASEDIR'
alias cleanit='cd $MYBASEDIR; rm management_dir* -r; rm *slurm'
export PATH=$HOME/local/bin:$PATH
```
Then run `source $HOME/.bashrc` to activate the new `.bashrc` file 

## Structure

We have a default folder structure, you need to create these folders:
- MYBASEDIR: typically on scratch
- MYBASEDIR/notebooks --> the contents should be kept in GitHub
- MYBASEDIR/results --> this is, where gnerated data goes
	--> for each notebook, there is (typically) one subfolder that is named exactly as the notebook is named
	--> notebooks start with the date they are created (YYYYMMDD)
- MYBASEDIR/prgr (optional), so far contains installers for anaconda, NEURON, ...

To replicate the folder structure run :

```bash
cd $MYBASEDIR
mkdir results
mkdir project_src
mkdir prgr
mkdir notebooks
```
## Repository

Clone `in_silico_framework` to `project_src`:

```bash
cd $MYBASEDIR/project_src
git clone https://github.com/research-center-caesar/in_silico_framework
```

Note: you will be asked for the credentials of your user account. 
You will need to use your personal access token (PAT) instead of the password.

## Install

In order to install `in-silico-framework` for both Python 2.7 and Python 3.8 run :

```bash
cd $MYBASEDIR/project_src/in_silico_framework/installer/py2.7
./install.sh $MYBASEDIR/anaconda_isf2
cd $MYBASEDIR/project_src/in_silico_framework/installer/py3.8
./install.sh $MYBASEDIR/anaconda_isf3
```

## Kernels

After the installation is completed, proceed to install the IPython Kernels:

```bash
source_isf; python -m ipykernel install --name root --user --display-name isf2
source_3; python -m ipykernel install --name base --user --display-name isf3
```
## Setting up VSCode

Open config file in VSCode and copy over the following replacing the username:
Host somalogin01
  HostName somalogin01
  User meulemeester

Host somacpu* somagpu*
  HostName %h
  User meulemeester
  ProxyCommand ssh -vv -W %h:%p somalogin01
  ProxyJump somalogin01

  Generate and SSH key using Powershell
  ssh-keygen -b 4096

  Download and install VScode extension "Remote -SSH" and copy over the public ssh key into trusted keys

## Cluster
The [SLURM_scripts](../SLURM_scripts/) module provides various modules for cluster control. Two scripts tend to be used a lot, so it is worth adding them as an alias to your ~/.bashrc. You can name these commands however you want.
```bash
alias submit="$MYBASEDIR/project_src/in_silico_framework/SLURM_scripts/submit.sh"
alias jupylink="$MYBASEDIR/project_src/in_silico_framework/SLURM_scripts/jupyter_link.sh"
```

Check if you can submit a job by requesting e.g. an interactive CPU partition (the `-c` and `-i` flags):

```bash
source_3
submit -ci session1
```

Make sure that the job appears with `Running` (R) status in slurm job queue:

```bash
squeue --me
```

If the job launched succesfully, you should see the links to the jupyter and notebook servers. If not, you can always fetch them:
```bash
jupylink session1
```

If this also doesn't work, then likely something went wrong during job submission. Check the output and error log of your job. It should appear in your `$MYBASEDIR` under the filename `[err/out].slurm.soma*pu08*.<id>.slurm`. If you can't find it, then the job probably didn't launch at all. Check the output of `squeue --me` and `sinfo` to see if there are any nodes available.

> __Warning__: It takes some time before the cluster has launched the jupyter server. You may need to wait a couple of seconds after submitting a job before this command will return a Jupyter link.

Use putty to open a SOCKS-5 proxy to the login node (somalogin01 or somalogin02)
 - you can do this with the -D option of the `ssh` command
    - example: `ssh -D 4040 somalogin02`
 - Open firefox settings, search for proxy and activate SOCKS-5 proxy. IP: 127.0.0.1, PORT: 4040 (or the port number passed to the ssh command)
 - this is explained in more detail in chantals google doc: https://docs.google.com/document/d/1S0IM7HgRsRdGXN_WFeDqPMOL3iDt1Obosuikzzc8YNc/edit#heading=h.dbift17bl1rt

You can now use firefox to run notebooks on the cluster by surfing to the link o fthe jupyter server. You may also run these notebooks in VSCode, or another IDE of choice. See [this StackOverflow answer](https://stackoverflowteams.com/c/ibs/questions/256) for more info.

## Ports

We have default ports
- 11112: jupyter notebook
- 11113: jupyter lab
- 28787: python 2 scheduler interface
- 28786: python 2 scheduler
- 38787: python 3 scheduler interface
- 38786: python 3 scheduler

## Extensions

We have a set of default extensions to `jupyter notebook`

- Codefolding in Editor
- Collapsible Headings
- contrib_nbextensions_help_item
- Nbextensions_dashboard tab
- Notify
- Codefolding
- Initialization cells
- Nbextensions edit menu item
- Table of Contents (2)

To install the extensions for `jupyter notebook` enter:

```bash
source_isf
jupyter contrib nbextension install --user
jupyter nbextensions_configurator enable --user
```

## Other config

It is recommended to override some settings in the distributed config yml file. In particular the amount of memory per worker, and whether or not dask should kill them if they eat up too much memory:

```yml
distributed:
  worker:
    memory:
      target: 0.90  # target fraction to stay below
	  spill:  False # fraction at which we spill to disk
	  pause: False  # fraction at which we pause worker threads
	  terminate: False  # fraction at which we terminate the worker
```
[This StackOverflow answer](https://stackoverflow.com/questions/57997463/dask-warning-worker-exceeded-95-memory-budget) gives more information.

An example on basic locking server config yml:
```yml
- config: {host: spock, port: 8885, socket_timeout: 1}
  type: redis
- config: {host: localhost, port: 6379, socket_timeout: 1}
  type: redis
```

## References

--> located at Z:\Share\HowTos\How-to use the AXON cluster.txt
--> https://docs.google.com/document/d/1S0IM7HgRsRdGXN_WFeDqPMOL3iDt1Obosuikzzc8YNc/edit#heading=h.dbift17bl1rt
--> [Setting up SSH Tunnels and port-forwarding with MobaXTerm](https://blog.mobatek.net/post/ssh-tunnels-and-port-forwarding/)
