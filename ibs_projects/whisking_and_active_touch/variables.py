quiescent_rates = {'L23': 0.53, 'L4ss': 0.72, 'L5st': 1.80, 'L5tt': 7.68, 'L6CC': 0.90, 'VPM': 0.97}
whisking_rates  = {'L23': 0.57, 'L4ss': 0.71, 'L5st': 2.04, 'L5tt': 8.21, 'L6CC': 0.24, 'VPM': 15.3}

touch_PSTHs_from_arco={
            'INT':  {'ongoing': 2.5377958374510645,  'onset': 22.813839530780736,  'sustained': 6.917082689875581},
            'L23':  {'ongoing': 0.47619047619047616, 'onset': 0.5833333333333334,  'sustained': 0.8333333333333333},
            'L4ss': {'ongoing': 0.9037168713639302,  'onset': 4.504862953138815,   'sustained': 2.4941313810006767},
            'L5ST': {'ongoing': 1.4357770278148136,  'onset': 1.0890981376857083,  'sustained': 1.7588271630292192},
            'L5TT': {'ongoing': 2.2751051645028393,  'onset': 10.062187104241602,  'sustained': 6.249914127110335},
            'L6CC': {'ongoing': 0.6100002452437489,  'onset': 17.432891411635506,  'sustained': 1.762409795740758},
            'VPM':  {'ongoing': 0.9702380952380952,  'onset': 16.416666666666668,  'sustained': 9.440104166666668}}

template_EXC = {'cellNr': None,
'celltype': {'pointcell': {'distribution': 'PSTH_poissontrain_v2', 'intervals': None, 'offset': 0.0, 'rates': None}},
'synapses': {'connectionFile': None, 'distributionFile': None,
    'receptors': {'glutamate_syn': {
        'delay': 0.0,
        'parameter': {'decayampa': 1.0, 'decaynmda': 1.0, 'facilampa': 0.0, 'facilnmda': 0.0, 'tau1': 26.0, 'tau2': 2.0, 'tau3': 2.0, 'tau4': 0.1}, 
        'threshold': 0.0,
        'weight': [None, None]}},
    'releaseProb': 0.6}}
template_INH= {'cellNr': None,
'celltype': {'pointcell': {'distribution': 'PSTH_poissontrain_v2','intervals': None, 'offset': 0.0, 'rates': None}},
'synapses': {'connectionFile': None, 'distributionFile': None,
    'receptors': {'gaba_syn': {
        'delay': 0.0,
        'parameter': {'decaygaba': 1.0, 'decaytime': 20.0, 'e': -80.0, 'facilgaba': 0.0, 'risetime': 1.0},
        'threshold': 0.0,
        'weight': 1.0}},
    'releaseProb': 0.25}}
template_info = {'author': 'abast', 'date': '23Sep2021', 'name': 'asd'}
template_NMODL_mechanisms = {'VecStim': '/', 'synapses': '/'}