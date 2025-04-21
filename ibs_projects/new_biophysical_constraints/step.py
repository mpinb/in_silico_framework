from biophysics_fitting.ephys import find_crossing
import Interface as I

# TTFS
def time_to_first_spike(t, v, thresh, stim_del):
    ti = find_crossing(v,thresh)[0][0]
    return t[ti] - stim_del

def ISI_CV_seminormalized(t,v,thresh, stim_del, mean):
    ttfs = time_to_first_spike(t, v, thresh, stim_del)
    return ttfs-mean

# DI
def doublet_ISI_check(t,v, thresh):
    return len(find_crossing(v,thresh)[0]) >=2

def doublet_ISI(t, v, thresh):
    ti = find_crossing(v,thresh)[0]
    ti = [t[ti] for ti in ti]
    return ti[1] - ti[0]

def doublet_ISI_seminormalized(t,v,thresh, mean):
    dbltISI = doublet_ISI(t,v,thresh)
    return I.np.abs(dbltISI - mean)
    
def spike_depth_abs_fast(t,v, thresh, return_times = False):
    d = []
    ti = find_crossing(v,thresh)[0]
    ti = [t[ti] for ti in ti]
    ts_list = []
    for lv in range(1, len(ti)-1):
        t_index_1 = list(t>=ti[lv]).index(True)
        if ti[lv+1] - ti[lv] < 5:
            t_index_2 = list(t>=ti[lv+1]).index(True)
        else:
            t_index_2 = list(t>=ti[lv] + 5).index(True)
        # print t_index_1, t_index_2, min(v[t_index_1:t_index_2+1])
        ii = I.np.argmin(v[t_index_1:t_index_2+1])
        d.append(v[t_index_1:t_index_2+1][ii])
        ts_list.append(t[t_index_1:t_index_2+1][ii])
    if return_times:
        return I.np.array(d), I.np.array(ts_list)
    else:
        return I.np.array(d)
    
def spike_depth_abs_fast_check(t,v, thresh, mean, std):
    ti = find_crossing(v,thresh)[0]
    if len(ti) < 3:
        return 20*std
    
def spike_depth_slow_time(t,v,thresh):
    d = []
    ti = find_crossing(v,thresh)[0]
    ti = [t[ti] for ti in ti]
    for lv in range(1, len(ti)-1):
        if ti[lv+1] - ti[lv] < 5:
            t_index_1 = list(t>=ti[lv]).index(True)
        else:
            t_index_1 = list(t>=ti[lv] + 5).index(True)
        t_index_2 = list(t>=ti[lv+1]).index(True)
        t_selected = t[t_index_1:t_index_2+1]
        v_selected = v[t_index_1:t_index_2+1]
        t_min = t_selected[I.np.argmin(v_selected)]
        isi = ti[lv+1] - ti[lv]
        dd = (t_min - ti[lv]) / (isi)
        d.append(dd)
    return I.np.array(d)

def spike_depth_abs_slow_check(t,v,thresh,mean,std):
    ti = find_crossing(v,thresh)[0]
    if len(ti) < 3:
        return 20*std
    
def mean_spike_depth_slow_time_seminormalized(t,v,thresh,mean):
    out = spike_depth_slow_time(t,v,thresh)
    return I.np.mean(I.np.abs(out - mean)) #- mean

def spike_depth_abs_slow(t,v,thresh,return_times = False):
    d = []
    ts_list = []
    ti = find_crossing(v,thresh)[0]
    ti = [t[ti] for ti in ti]
    for lv in range(1, len(ti)-1):
        if ti[lv+1] - ti[lv] < 5:
            t_index_1 = list(t>=ti[lv]).index(True)
        else:
            t_index_1 = list(t>=ti[lv] + 5).index(True)
        t_index_2 = list(t>=ti[lv+1]).index(True)
        ii = I.np.argmin(v[t_index_1:t_index_2+1])
        d.append(v[t_index_1:t_index_2+1][ii])
        ts_list.append(t[t_index_1:t_index_2+1][ii])
    if return_times:
        return I.np.array(d), I.np.array(ts_list)
    else:
        return I.np.array(d)
    
def spike_depth_abs_slow_check(t,v,thresh,mean,std):
    ti = find_crossing(v,thresh)[0]
    if len(ti) < 3:
        return 20*std
    
def mean_spike_depth_abs_slow_seminormalized(t,v,thresh,mean):
    out = spike_depth_abs_slow(t,v,thresh)
    return I.np.mean(I.np.abs(out - mean)) #- mean

def mean_frequency2(t,v,thresh,stim_duration):
    ti = find_crossing(v,thresh)[0]
    ti = [t[ti] for ti in ti]
    r = float(len(ti)) * 1000. / stim_duration
    return r
    
    
def mean_frequency2_check(t,v,thresh,mean,stim_offset,stim_duration):
    r = mean_frequency2(t,v,threshmean,std,stim_offset,stim_duration)
    ti = find_crossing(v,thresh)[0]
    ti = [t[ti] for ti in ti]
    if stim_offset + stim_duration - ti[-1] > 2. * 1000./r:
        return False
    else:
        return True
    
def mean_frequency2_seminormalized(t,v,thresh,stim_duration,mean):
    f = mean_frequency2(t,v,thresh,stim_duration)
    return f-mean

def adaptation_index2(t, v, thresh, stim_offset, stim_duration):
    ti = find_crossing(v, thresh)[0]
    spike_times = I.np.array([t[ti] for ti in ti])
    spike_times_without_first = spike_times[1:]
    isis = spike_times_without_first[1:] - spike_times_without_first[:-1]
    l = stim_offset+stim_duration - spike_times[-1]
    if l>0 and l > isis[-1]:
        I.np.array(list(isis).append(l))
    
    adis = isis[1:]-isis[:-1]
    adis = adis / (isis[1:] + isis[:-1])
    
    return adis

def adaptation_index2_seminormalized(t,v,thresh,stim_offset,stim_duration,mean):
    return I.np.mean(adaptation_index2(t, v, thresh, stim_offset, stim_duration)) - mean

def ISI_CV_check(t,v, thresh):
    return len(find_crossing(v,thresh)[0]) >=5

def ISI_CV(t, v, thresh):
    ti = find_crossing(v,thresh)[0]
    #print len(ti)
    ti = [t[ti] for ti in ti]
    ti = I.np.array(ti[1:]) # discard first spike
    isi = ti[1:] - ti[:-1]
    #print isi
    #print I.np.std(isi)
    #print I.np.mean(isi)
    return I.np.std(isi, ddof=1) / I.np.mean(isi)

def ISI_CV_seminormalized(t,v,thresh, mean):
    isi_cv = ISI_CV(t,v,thresh)
    return I.np.mean(I.np.abs(isi_cv)) - mean

def get_step_response_evaluation(vt):

    out = {}
    thresh = -30
    t1,v1 = vt['StepOne.hay_measure']['tVec'], vt['StepOne.hay_measure']['vList'][0]
    t2,v2 = vt['StepTwo.hay_measure']['tVec'], vt['StepTwo.hay_measure']['vList'][0]
    t3,v3 = vt['StepThree.hay_measure']['tVec'], vt['StepThree.hay_measure']['vList'][0]

    ###############################
    # TTFS
    ###############################

    mean_1, std_1 = 43.2500, 7.3200 # TTFS1
    mean_2, std_2 = 19.1250,7.3100  # TTFS2
    mean_3, std_3 = 7.2500, 1.0000 # TTFS3

    out['TTFS1.raw'] = ttfs1 = time_to_first_spike(t1,v1,thresh,700)
    out['TTFS2.raw'] = ttfs2 = time_to_first_spike(t2,v2,thresh,700)
    out['TTFS3.raw'] = ttfs3 = time_to_first_spike(t3,v3,thresh,700)
    out['TTFS1'] = (ttfs1 - mean_1)/std_1
    out['TTFS2'] = (ttfs2 - mean_2)/std_2
    out['TTFS3'] = (ttfs3 - mean_3)/std_3

    ###############################
    # DI
    ###############################

    mean_1, std_1 = 57.7500, 33.4800 # DI1
    mean_2, std_2 = 6.6250, 8.6500 # DI2
    mean_3, std_3 = 5.38, 0.83 # DI3

    out['DI1.raw'] = DI1 = doublet_ISI(t1,v1,thresh)
    out['DI2.raw'] = DI2 = doublet_ISI(t2,v2,thresh)
    out['DI3.raw'] = DI3 = doublet_ISI(t3,v3,thresh)

    out['DI1'] = (DI1 - mean_1)/std_1
    out['DI2'] = (DI2 - mean_2)/std_2
    out['DI3'] = (DI3 - mean_3)/std_3

    # 'DI1': 0.07759285829347992, 0.077592858293479922, check
    # 'DI2': 3.1244060834841667, 3.1244060834841667, check
    # 'DI3': NaN, 3.3917404589676856

    ##############################################
    # mean AP height
    ##############################################
    from biophysics_fitting.ephys import AP_height
    mean_1, std_1 = 26.2274, 4.9703 
    mean_2, std_2 = 16.5209, 6.1127
    mean_3, std_3 = 16.4368, 6.9322

    out['APh1.raw'] = APh1 = AP_height(t1,v1,thresh).mean()
    out['APh2.raw'] = APh2 = AP_height(t2,v2,thresh).mean()
    out['APh3.raw'] = APh3 = AP_height(t3,v3,thresh).mean()

    out['APh1'] = (APh1 - mean_1)/std_1
    out['APh2'] = (APh2 - mean_2)/std_2
    out['APh3'] = (APh3 - mean_3)/std_3


    # 'APh1': 1.132973274786074, -1.1329732747860739 # check
    # 'APh2': 0.6633159547283898, 0.66331595472839011 # check
    # 'APh3': 0.45358816252661, 0.45358816252661022 # check

    ################################################
    # mean AP width
    ################################################
    from biophysics_fitting.ephys import AP_width
    mean_1, std_1 = 1.3077, 0.1665
    mean_2, std_2 = 1.3833, 0.2843
    mean_3, std_3 = 1.8647, 0.4119

    out['APw1.raw'] = APw1 = AP_width(t1,v1,thresh).mean()
    out['APw2.raw'] = APw2 = AP_width(t2,v2,thresh).mean()
    out['APw3.raw'] = APw3 = AP_width(t3,v3,thresh).mean()

    out['APw1'] = (APw1 - mean_1)/std_1
    out['APw2'] = (APw2 - mean_2)/std_2
    out['APw3'] = (APw3 - mean_3)/std_3

    #'APh1': 1.132973274786074,-1.1329732747860739 # check
    #'APh2': 0.6633159547283898,0.66331595472839011 # check
    #'APh3': 0.45358816252661,0.45358816252661022 # check



    ################################################
    # fast afterhyperpolarization
    ################################################

    mean_1, std_1 = -51.9511, 5.8213 
    mean_2, std_2 = -54.1949, 5.5706 
    mean_3, std_3 = -56.5579, 3.5834

    out['fAHPd1.raw'] = fAHPd1 = spike_depth_abs_fast(t1,v1,thresh).mean()
    out['fAHPd2.raw'] = fAHPd2 = spike_depth_abs_fast(t2,v2,thresh).mean()
    out['fAHPd3.raw'] = fAHPd3 = spike_depth_abs_fast(t3,v3,thresh).mean()

    # I.np.mean(I.np.abs(out - mean))

    out['fAHPd1'] = (fAHPd1 - mean_1)/std_1
    out['fAHPd2'] = (fAHPd2 - mean_2)/std_2
    out['fAHPd3'] = (fAHPd3 - mean_3)/std_3

    #'fAHPd1': 2.176689724921884, -2.1766897249218826,
    #'fAHPd2': 1.8401396965571535,-1.8401396965571528,
    #'fAHPd3': 1.9157610706811778,-1.915761070681179,

    ###############################################
    # slow afterhyperpolarization
    ###############################################
    mean_1, std_1 = -58.0443, 4.5814 
    mean_2, std_2 = -60.5129, 4.6717
    mean_3, std_3 = -59.9923, 3.9247 

    out['sAHPd1.raw'] = sAHPd1 = spike_depth_abs_slow(t1,v1,thresh).mean()
    out['sAHPd2.raw'] = sAHPd2 = spike_depth_abs_slow(t2,v2,thresh).mean()
    out['sAHPd3.raw'] = sAHPd3 = spike_depth_abs_slow(t3,v3,thresh).mean()

    # I.np.mean(I.np.abs(out - mean))

    out['sAHPd1'] = (sAHPd1 - mean_1)/std_1
    out['sAHPd2'] = (sAHPd2 - mean_2)/std_2
    out['sAHPd3'] = (sAHPd3 - mean_3)/std_3

    # 'sAHPd1': 1.388876026948427, 'sAHPd1': -1.3888760269484262, # check
    # 'sAHPd2': 0.752929952147098, 'sAHPd2': -0.75292995214709713, # check
    # 'sAHPd3': 0.6605872327804491, 'sAHPd3': -0.66058723278044884, # check


    ###################################
    # slow AHP time
    ##################################
    mean_1, std_1 = 0.2376, 0.0299 
    mean_2, std_2 = 0.2787, 0.0266 
    mean_3, std_3 = 0.2131, 0.0368

    out['sAHPt1.raw'] = sAHPt1 = spike_depth_slow_time(t1,v1,thresh).mean()
    out['sAHPt2.raw'] = sAHPt2 = spike_depth_slow_time(t2,v2,thresh).mean()
    out['sAHPt3.raw'] = sAHPt3 = spike_depth_slow_time(t3,v3,thresh).mean()

    # I.np.mean(I.np.abs(out - mean))

    out['sAHPt1'] = (sAHPt1 - mean_1)/std_1
    out['sAHPt2'] = (sAHPt2 - mean_2)/std_2
    out['sAHPt3'] = (sAHPt3 - mean_3)/std_3

    # 'sAHPt1': -2.9318467722569035, 2.9318467722569035 # check!
    # 'sAHPt2': -3.1306697662323146, 3.1306697662323155 # check!
    # 'sAHPt3': -2.5006782234918741, 2.5006782234918736 # check!

    ##################################
    # mean frequency
    ###################################

    mean_1, std_1 = 9.0000, 0.8800 
    mean_2, std_2 = 14.5000, 0.5600 
    mean_3, std_3 = 22.5000, 2.2222 

    out['mf1.raw'] = mf1 = mean_frequency2(t1,v1,thresh, 2000)
    out['mf2.raw'] = mf2 = mean_frequency2(t2,v2,thresh, 2000)
    out['mf3.raw'] = mf3 = mean_frequency2(t3,v3,thresh, 2000)

    out['mf1'] = (mf1 - mean_1)/std_1
    out['mf2'] = (mf2 - mean_2)/std_2
    out['mf3'] = (mf3 - mean_3)/std_3

    # 'mf1': 0.5681818181818182, 0.5681818181818182,
    # 'mf2': -0.8928571428571428, 0.8928571428571428,
    # 'mf3': 0.6750067500675007, 0.6750067500675007,

    #####################################
    # adaptation index
    #####################################
    mean_1, std_1 = 0.0036, 0.0091 
    mean_2, std_2 = 0.0023, 0.0056 
    mean_3, std_3 = 0.0046, 0.0026 

    out['AI1.raw'] = AI1 = adaptation_index2(t1,v1,thresh, 700, 2000).mean()
    out['AI2.raw'] = AI2 = adaptation_index2(t2,v2,thresh, 700, 2000).mean()
    out['AI3.raw'] = AI3 = adaptation_index2(t3,v3,thresh, 700, 2000).mean()

    out['AI1'] = (AI1 - mean_1)/std_1
    out['AI2'] = (AI2 - mean_2)/std_2
    out['AI3'] = (AI3 - mean_3)/std_3

    # 'AI1': 0.85006184451696842, 'AI1': 0.8500618445169685,
    # 'AI2': 1.2497210695674865, 'AI2': 1.2497210695674867,
    # 'AI3': 0.81789302343320602, 'AI3': 0.8178930234332054,

    #####################################
    # ISI CV
    #####################################

    mean_1, std_1 = 0.1204, 0.0321 
    mean_2, std_2 = 0.1083, 0.0368 
    mean_3, std_3 = 0.0954, 0.0140 

    out['ISIcv1.raw'] = ISIcv1 = ISI_CV(t1,v1,thresh)
    out['ISIcv2.raw'] = ISIcv2 = ISI_CV(t2,v2,thresh)
    out['ISIcv3.raw'] = ISIcv3 = ISI_CV(t3,v3,thresh)

    out['ISIcv1'] = (ISIcv1 - mean_1)/std_1
    out['ISIcv2'] = (ISIcv2 - mean_2)/std_2
    out['ISIcv3'] = (ISIcv3 - mean_3)/std_3


    # 'ISIcv1': 0.4738587281203163, 'ISIcv1': -0.47385872812031632,
    # 'ISIcv2': 0.20629487441654829, 'ISIcv2': -0.20629487441654754,
    # 'ISIcv3': 0.18542629252363374, 'ISIcv3': 0.18542629252363174,
    
    out = {'step_post_hoc_evaluation.' + k:v for k,v in out.items()}
    return out