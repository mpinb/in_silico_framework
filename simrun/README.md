# simrun

Together with [simrun](../simrun/), this module provides high-level acces to run many simulation trials in a scalable way (making use of the high-performance cluster). They make heavy use of the [single cell parser](../single_cell_parser/) module.

## Running new simulations

ds = I.simrun_run_new_simulations(neup_path, netp_path, dirPrefix, nSweeps, nprocs, tStop) <br/>
neup_path --- neuron param file  <br/>
netp_path --- network param file <br/>
dirPrefix = outdir.join(output_name) --- where the results are going to be saved <br/>
nSweeps = 200 --- number of simulations=trials to run in each process <br/>
nprocs = 14000 --- number of processes running #sum(client.ncores().values()), total number of simulations you perform is nSweeps*nprocs <br/>
tStop = offset + 100 --- offset: time the system needs to reach the steady state (200-500ms), tStop: time you want to simulate <br/>

## Simulation results
When running many simulation trials, each one is executed in a process using a specific neuron and network parameter files. Each process can run one or more simulation trials in series but a simulation trial can only run in a single process. Therefore, the total amount of trials you are going to simulate is nSweeps*nprocs.
Each subprocess creates a subfolder in the results folder, naming it based on when it run, the process ID, and the seed used. The name is unique to avoid having 2 processes writing in the same file. Inside the subfolders the files are generated:
- empty file with the name of the machine where the simulation run. 
- network and neuron param files used for that simulation. Therefore, it is less memory efficient to have many processes and less sweeps (the network and neuron param files are going to be repeated many times).
- csv files: output of the simulation. called runxxxx. the number xxxx corresponds to the sweep number. 
- presynaptic cells
- synapses
- vm_all_traces: vm at soma
- vm_dend_traces_somaDist: vm at dendrites at a soma distance of 834.2
- vm_dend_traces_somaDist: vm at dendrites at a soma distance of 660.7
In order to trace the voltage are more locations, this should be specified in the neuron parameter file.

## Reformatting simulation results
I.db_init_simrun_general.init gathers the results and brings them to a format is convenient to work with. It creates a db that has a standardized structure.

I.db_init_simrun_general.init(db.create_sub_db('dbs', raise_ = False).create_sub_db(output_name, raise_ = False), 
                                   simresult_path=outdir.join(output_name), 
                                   core = True, voltage_traces=True, parameterfiles =True,
                                   rewrite_in_optimized_format = True,
                                   dendritic_spike_times_threshold = -30.0,
                                   client = client)

if rewrite_in_optimized_format == True: fills db with data, writes it in (fast) binary format and combines it such that no matter how many simulation trials you have, you get max 5000 files. For interactive/testing results to False.

The resulting db will have:
- synapse_activation dataframe: dask (not pandas) dataframe since it is very large and often it wouldn't fit in memory.
- cell_activation pandas (not dask) dataframe
- spike_times dataframe: pandas (not dask) dataframe because it's relatively compact. Maybe GB if you do a huge simulation but not more.
