# SLURM scripts

## Submitting a job / requesting resources
This directory provides various scripts to interact with the HPC job manager SLURM. You can request resources by either
- running specific shell scripts for SOMA or AXON that have various variables hard-coded
- running `submit.sh` and passing parameters as command-line arguments. Run `submit -h` for help on how to use it and which arguments are possible.

## What does it mean to "submit a job"
All the shell scripts except `jupylink.sh` will invoke a python script that will set up:
- A management directory of the current job
- DASK: a Python process manager that allows python to be very parallellised, with native support for pandas and other modules.
- Jupyter: both a Notebook server and a JupyterLab server will be started on port 11112 and 11113 respectively
- File locking: to make sure nobody can write/read the same file at the same time, which will corrupt the data

## Jupyter links
`jupyter_link.sh` is a small script that checks the error log of some job for a jupyter link. This simply saves some time. It takes the job name as an argument.