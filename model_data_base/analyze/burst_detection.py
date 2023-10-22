## deprecated 12.02.2021 rieke / arco

# import pandas as pd
# import dask
# import dask.dataframe as dd
# # from compatibility import multiprocessing_scheduler

# def burst_detection_helper(proximal_voltage_series, st, burst_cutoff):
#     sim_trial_index = proximal_voltage_series.name
#     spike_times = st.loc[sim_trial_index]
#     #bursts need to consist of more than one spike
#     if len(spike_times) <=2:
#         return pd.Series()

#     out = [] #list of tuples of form (first_spike_of_burst, last_spike_of_burst, n_spikes_in_burst)
#     for lv in range(len(spike_times)-1):
#         spike = spike_times[lv]
#         next_spike = spike_times[lv+1]
#         voltage_dummy = proximal_voltage_series[(proximal_voltage_series.index >= spike) & \
#                                                     (proximal_voltage_series.index < next_spike)]
#         assert isinstance(proximal_voltage_series, pd.Series)

#         voltage_dummy = voltage_dummy.min()
#         if voltage_dummy >= burst_cutoff:
#             if out and out[-1][1] == spike:
#                 #this is true, if i found one more spike belonging to already detected burst
#                 #--> increase counter
#                 out[-1] = (out[-1][0], next_spike, out[-1][2] + 1)
#             else:
#                 #this is executed, if a new burst is found
#                 out.append((spike, next_spike, 2))

#     out_dict = {}
#     for lv, x in enumerate(out):
#         out_dict[str(lv)+'_first'] = x[0]
#         out_dict[str(lv)+'_last'] = x[1]
#         out_dict[str(lv)+'_count'] = x[2]

#     pd.Series(out_dict)
#     return pd.Series(out_dict)

# def burst_detection_pd(pdf, st, burst_cutoff):
#     fun = lambda x: burst_detection_helper(x, st, burst_cutoff)
#     return pdf.apply(fun, axis = 1)

# def burst_detection(ddf, st, burst_cutoff = -55):
#     '''searches for bursts. The idea is, that if the voltage in between two spikes
#     at the "hot zone" does not drop below a certain value (burst_cutoff), these
#     two spikes belong to a burst.

#     Expected input:
#     ddf: dask dataframe or pandas dataframe of voltage traces
#         recorded near the "hot zone"
#     st: pandas dataframe containing the spike times
#     burst_cutoff: lower limit of voltage. If voltage at hot zone stays above this value,
#         the two spikes are considered to belong to a burst

#     Output:
#         pandas dataframe with the following format:
#               |0_count|0_first|0_last| ...
#         |index|

#     [number]_count is the number of consecutive spikes forming the burst
#     [number]_first is the timepoint of the first spike of the burst
#     [number]_last is the timepoint of the last spike of the burst

#     '''

#     if isinstance(ddf, pd.DataFrame):
#         return burst_detection_pd(ddf, st, burst_cutoff)
#     if isinstance(ddf, dd.DataFrame):
#         delayed_fun = dask.delayed(lambda x: burst_detection_pd(x, st, burst_cutoff))
#         dummy = dask.compute(*list(map(delayed_fun, ddf.to_delayed())), get = multiprocessing_scheduler)
#         return pd.concat(dummy)
