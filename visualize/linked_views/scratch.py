import numpy as np
import util
import matplotlib.pyplot as plt
import pandas as pd
import itertools
import json
import vaex
import vaex.ml

filename = "/scratch/visual/bzfharth/in-silico-install-dir/project_src/in_silico_framework/getting_started/linked-views-example-data/backend_data_2023-06-22/simulation_samples.csv"
df = vaex.from_csv(filename, copy_index=False)

def getParamsCols():
    params_py2 = ['ephys.CaDynamics_E2.apic.decay',
        'ephys.CaDynamics_E2.apic.gamma', 'ephys.CaDynamics_E2.axon.decay',
        'ephys.CaDynamics_E2.axon.gamma', 'ephys.CaDynamics_E2.soma.decay',
        'ephys.CaDynamics_E2.soma.gamma', 'ephys.Ca_HVA.apic.gCa_HVAbar',
        'ephys.Ca_HVA.axon.gCa_HVAbar', 'ephys.Ca_HVA.soma.gCa_HVAbar',
        'ephys.Ca_LVAst.apic.gCa_LVAstbar', 'ephys.Ca_LVAst.axon.gCa_LVAstbar',
        'ephys.Ca_LVAst.soma.gCa_LVAstbar', 'ephys.Im.apic.gImbar',
        'ephys.K_Pst.axon.gK_Pstbar', 'ephys.K_Pst.soma.gK_Pstbar',
        'ephys.K_Tst.axon.gK_Tstbar', 'ephys.K_Tst.soma.gK_Tstbar',
        'ephys.NaTa_t.apic.gNaTa_tbar', 'ephys.NaTa_t.axon.gNaTa_tbar',
        'ephys.NaTa_t.soma.gNaTa_tbar', 'ephys.Nap_Et2.axon.gNap_Et2bar',
        'ephys.Nap_Et2.soma.gNap_Et2bar', 'ephys.SK_E2.apic.gSK_E2bar',
        'ephys.SK_E2.axon.gSK_E2bar', 'ephys.SK_E2.soma.gSK_E2bar',
        'ephys.SKv3_1.apic.gSKv3_1bar', 'ephys.SKv3_1.apic.offset',
        'ephys.SKv3_1.apic.slope', 'ephys.SKv3_1.axon.gSKv3_1bar',
        'ephys.SKv3_1.soma.gSKv3_1bar', 'ephys.none.apic.g_pas',
        'ephys.none.axon.g_pas', 'ephys.none.dend.g_pas',
        'ephys.none.soma.g_pas', 'scale_apical.scale']

    params_py3 = [p.replace('ephys.CaDynamics_E2', 'ephys.CaDynamics_E2_v2') for p in params_py2]
    return params_py3

def append_PCA(df, columns, descriptor, n_components = 2):
    pca = vaex.ml.PCA(features=columns, n_components=n_components)    
    df_transformed = pca.fit_transform(df)
    for component_idx in range(0, n_components):
        df_transformed.rename("PCA_{}".format(component_idx), "{}-{}".format(descriptor, component_idx+1))
    print(df_transformed.get_column_names())


print(len(list(df.columns)))

append_PCA(df, getParamsCols()[0:5], "PCA-ephys")