# Configuration

This directory contains example files on how you can configure your own experience with ISF.

## Necessary configurations
The `git` command needs to be configured in order to use ISF. We recommend `git v2.31`. Make sure you have `git` installed and your shell can find the command (you can check this by typing `which git`).

## Recommended configurations

### Dask configuration
Dask automatically looks for files such as `distributed.yaml` throughout the entire codebase (like the one you find [here](./distributed_example.yaml)) for configuration. 

Dask automatically kill workers once they exceed 95% of the memory budget, which can be especially frustrating if you are doing a project where this is not a particular problematic thing to the point of terminating the worker without further ado (e.g. when working on a HPC). It can be useful to adapt this behavior. [This way](./distributed_example.yaml), you can configure workers to not be terminated or paused when they exceed memory 
```yml
distributed:
  worker:
    memory:
      target: 0.90  # target fraction to stay below
	  spill:  False # fraction at which we spill to disk
	  pause: False  # fraction at which we pause worker threads
	  terminate: False  # fraction at which we terminate the worker
```
(See this question on [StackOverflow](https://stackoverflow.com/questions/57997463/dask-warning-worker-exceeded-95-memory-budget))

## Automatic workflows
The workflow files in [.github/workflows](.github/workflows) define automatic workflows that run as soon as some trigger event happens. This trigger event is currently defined as push and pull requests on (almost) all branches. We have set up a local machine with (since last update) 8 runners and 10TB of disk space to take care of parallellized testing for speedy development. Upon such trigger event, it will perform the following actions:
1. Fetch the previous commit on the runner
2. Based on the commit it receives, figure out if a rebuild of the codebase is necessary
  a. Does a previous build already exists on the runner?
  b. Was the previous build succesful?
  c. Do the changes in the current commit not warrant a rebuild (i.e. they are not changes in the .github/workflows, testing/, or installer/ folder)
  If the answer is yes to all these, it will skip the build process, otherwise it will (re)build the codebase
3. Run the test suite

