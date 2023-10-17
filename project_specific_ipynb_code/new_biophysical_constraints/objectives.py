import project_specific_ipynb_code.biophysical_models
objectives_BAC = project_specific_ipynb_code.biophysical_models.objectives_BAC
objectives_step = project_specific_ipynb_code.biophysical_models.objectives_step
objectives_2BAC = ['1BAC_APheight', '1BAC_ISI', '1BAC_ahpdepth', '1BAC_caSpike_height', '1BAC_caSpike_width', '1BAC_spikecount', '2BAC_APheight', '2BAC_ISI', '2BAC_ahpdepth', '2BAC_caSpike_height', '2BAC_caSpike_width', '2BAC_spikecount', 'bAP_APheight', 'bAP_APwidth', 'bAP_att2', 'bAP_att3', 'bAP_spikecount']

# below is added for incremental evaluation
objectives_bAP = ['bAP_APheight','bAP_APwidth','bAP_att2','bAP_att3','bAP_spikecount']
objectives_BAC2_only = ['1BAC_APheight', '1BAC_ISI', '1BAC_ahpdepth', '1BAC_caSpike_height', '1BAC_caSpike_width', '1BAC_spikecount', '2BAC_APheight', '2BAC_ISI', '2BAC_ahpdepth', '2BAC_caSpike_height', '2BAC_caSpike_width', '2BAC_spikecount']
objectives_step1 = [o for o in objectives_step if o.endswith('1')]
objectives_step2 = [o for o in objectives_step if o.endswith('2')]
objectives_step3 = [o for o in objectives_step if o.endswith('3')]
objectives_hyperpolarizing = ['hyperpolarizing.Sag', 'hyperpolarizing.Attenuation', 'hyperpolarizing.Dend_Rin', 'hyperpolarizing.Rin']

objectives_crit_freq = ['crit_freq.frequency_error', 
                        'crit_freq.num_spikes_error']

objectives_chrip = ['chirp.res_freq',
 'chirp.res_freq_dend',
 'chirp.transfer_dend',
 'chirp.synch_freq']

objectives_by_stimulus = {'bAP': objectives_bAP,
                   'BAC': objectives_BAC2_only, 
                   'StepOne': objectives_step1, 
                   'StepTwo': objectives_step2, 
                   'StepThree': objectives_step3}