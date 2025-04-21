# has code to both record energy metrics and calculate ATP etc. from the recorded metrics such as total charge exchanged 
import Interface as I 
import numpy as np
from scipy.integrate import trapz
import scipy.constants
from .utils import find_label 

membrane_currents = ['pas.i', 
                   'NaTa_t.ina','Nap_Et2.ina','Ca_HVA.ica',
                   'Ca_LVAst.ica','SKv3_1.ik','SK_E2.ik','Ih.ihcn','Im.ik',
                   'K_Pst.ik','K_Tst.ik', 'net_axial', 'i_cap']

new_energy_metrics = ['new_EM_A_bifurcation_axial_integral_frac',
 'new_EM_A_bifurcation_depolarizing_membrane_current_integral',
 'new_EM_A_bifurcation_hyperpolarizing_membrane_current_integral',
 'new_EM_B_bifurcation_overlap',
 'new_EM_E_depo_charge_exchanged_dend_vs_soma',
 'new_EM_D_charge_exchanged_Myelin_pas.i',
 'new_EM_D_charge_exchanged_Myelin_NaTa_t.ina',
 'new_EM_D_charge_exchanged_Myelin_Nap_Et2.ina',
 'new_EM_D_charge_exchanged_Myelin_Ca_HVA.ica',
 'new_EM_D_charge_exchanged_Myelin_Ca_LVAst.ica',
 'new_EM_D_charge_exchanged_Myelin_SKv3_1.ik',
 'new_EM_D_charge_exchanged_Myelin_SK_E2.ik',
 'new_EM_D_charge_exchanged_Myelin_Ih.ihcn',
 'new_EM_D_charge_exchanged_Myelin_Im.ik',
 'new_EM_D_charge_exchanged_Myelin_K_Pst.ik',
 'new_EM_D_charge_exchanged_Myelin_K_Tst.ik',
 'new_EM_D_charge_exchanged_Myelin_net_axial',
 'new_EM_D_charge_exchanged_Myelin_i_cap',
 'new_EM_D_absolute_charge_exchanged_Myelin_pas.i',
 'new_EM_D_absolute_charge_exchanged_Myelin_NaTa_t.ina',
 'new_EM_D_absolute_charge_exchanged_Myelin_Nap_Et2.ina',
 'new_EM_D_absolute_charge_exchanged_Myelin_Ca_HVA.ica',
 'new_EM_D_absolute_charge_exchanged_Myelin_Ca_LVAst.ica',
 'new_EM_D_absolute_charge_exchanged_Myelin_SKv3_1.ik',
 'new_EM_D_absolute_charge_exchanged_Myelin_SK_E2.ik',
 'new_EM_D_absolute_charge_exchanged_Myelin_Ih.ihcn',
 'new_EM_D_absolute_charge_exchanged_Myelin_Im.ik',
 'new_EM_D_absolute_charge_exchanged_Myelin_K_Pst.ik',
 'new_EM_D_absolute_charge_exchanged_Myelin_K_Tst.ik',
 'new_EM_D_absolute_charge_exchanged_Myelin_net_axial',
 'new_EM_D_absolute_charge_exchanged_Myelin_i_cap',
 'new_EM_D_charge_exchanged_trunk_pas.i',
 'new_EM_D_charge_exchanged_trunk_NaTa_t.ina',
 'new_EM_D_charge_exchanged_trunk_Nap_Et2.ina',
 'new_EM_D_charge_exchanged_trunk_Ca_HVA.ica',
 'new_EM_D_charge_exchanged_trunk_Ca_LVAst.ica',
 'new_EM_D_charge_exchanged_trunk_SKv3_1.ik',
 'new_EM_D_charge_exchanged_trunk_SK_E2.ik',
 'new_EM_D_charge_exchanged_trunk_Ih.ihcn',
 'new_EM_D_charge_exchanged_trunk_Im.ik',
 'new_EM_D_charge_exchanged_trunk_K_Pst.ik',
 'new_EM_D_charge_exchanged_trunk_K_Tst.ik',
 'new_EM_D_charge_exchanged_trunk_net_axial',
 'new_EM_D_charge_exchanged_trunk_i_cap',
 'new_EM_D_absolute_charge_exchanged_trunk_pas.i',
 'new_EM_D_absolute_charge_exchanged_trunk_NaTa_t.ina',
 'new_EM_D_absolute_charge_exchanged_trunk_Nap_Et2.ina',
 'new_EM_D_absolute_charge_exchanged_trunk_Ca_HVA.ica',
 'new_EM_D_absolute_charge_exchanged_trunk_Ca_LVAst.ica',
 'new_EM_D_absolute_charge_exchanged_trunk_SKv3_1.ik',
 'new_EM_D_absolute_charge_exchanged_trunk_SK_E2.ik',
 'new_EM_D_absolute_charge_exchanged_trunk_Ih.ihcn',
 'new_EM_D_absolute_charge_exchanged_trunk_Im.ik',
 'new_EM_D_absolute_charge_exchanged_trunk_K_Pst.ik',
 'new_EM_D_absolute_charge_exchanged_trunk_K_Tst.ik',
 'new_EM_D_absolute_charge_exchanged_trunk_net_axial',
 'new_EM_D_absolute_charge_exchanged_trunk_i_cap',
 'new_EM_D_charge_exchanged_oblique_pas.i',
 'new_EM_D_charge_exchanged_oblique_NaTa_t.ina',
 'new_EM_D_charge_exchanged_oblique_Nap_Et2.ina',
 'new_EM_D_charge_exchanged_oblique_Ca_HVA.ica',
 'new_EM_D_charge_exchanged_oblique_Ca_LVAst.ica',
 'new_EM_D_charge_exchanged_oblique_SKv3_1.ik',
 'new_EM_D_charge_exchanged_oblique_SK_E2.ik',
 'new_EM_D_charge_exchanged_oblique_Ih.ihcn',
 'new_EM_D_charge_exchanged_oblique_Im.ik',
 'new_EM_D_charge_exchanged_oblique_K_Pst.ik',
 'new_EM_D_charge_exchanged_oblique_K_Tst.ik',
 'new_EM_D_charge_exchanged_oblique_net_axial',
 'new_EM_D_charge_exchanged_oblique_i_cap',
 'new_EM_D_absolute_charge_exchanged_oblique_pas.i',
 'new_EM_D_absolute_charge_exchanged_oblique_NaTa_t.ina',
 'new_EM_D_absolute_charge_exchanged_oblique_Nap_Et2.ina',
 'new_EM_D_absolute_charge_exchanged_oblique_Ca_HVA.ica',
 'new_EM_D_absolute_charge_exchanged_oblique_Ca_LVAst.ica',
 'new_EM_D_absolute_charge_exchanged_oblique_SKv3_1.ik',
 'new_EM_D_absolute_charge_exchanged_oblique_SK_E2.ik',
 'new_EM_D_absolute_charge_exchanged_oblique_Ih.ihcn',
 'new_EM_D_absolute_charge_exchanged_oblique_Im.ik',
 'new_EM_D_absolute_charge_exchanged_oblique_K_Pst.ik',
 'new_EM_D_absolute_charge_exchanged_oblique_K_Tst.ik',
 'new_EM_D_absolute_charge_exchanged_oblique_net_axial',
 'new_EM_D_absolute_charge_exchanged_oblique_i_cap',
 'new_EM_D_charge_exchanged_Soma_pas.i',
 'new_EM_D_charge_exchanged_Soma_NaTa_t.ina',
 'new_EM_D_charge_exchanged_Soma_Nap_Et2.ina',
 'new_EM_D_charge_exchanged_Soma_Ca_HVA.ica',
 'new_EM_D_charge_exchanged_Soma_Ca_LVAst.ica',
 'new_EM_D_charge_exchanged_Soma_SKv3_1.ik',
 'new_EM_D_charge_exchanged_Soma_SK_E2.ik',
 'new_EM_D_charge_exchanged_Soma_Ih.ihcn',
 'new_EM_D_charge_exchanged_Soma_Im.ik',
 'new_EM_D_charge_exchanged_Soma_K_Pst.ik',
 'new_EM_D_charge_exchanged_Soma_K_Tst.ik',
 'new_EM_D_charge_exchanged_Soma_net_axial',
 'new_EM_D_charge_exchanged_Soma_i_cap',
 'new_EM_D_absolute_charge_exchanged_Soma_pas.i',
 'new_EM_D_absolute_charge_exchanged_Soma_NaTa_t.ina',
 'new_EM_D_absolute_charge_exchanged_Soma_Nap_Et2.ina',
 'new_EM_D_absolute_charge_exchanged_Soma_Ca_HVA.ica',
 'new_EM_D_absolute_charge_exchanged_Soma_Ca_LVAst.ica',
 'new_EM_D_absolute_charge_exchanged_Soma_SKv3_1.ik',
 'new_EM_D_absolute_charge_exchanged_Soma_SK_E2.ik',
 'new_EM_D_absolute_charge_exchanged_Soma_Ih.ihcn',
 'new_EM_D_absolute_charge_exchanged_Soma_Im.ik',
 'new_EM_D_absolute_charge_exchanged_Soma_K_Pst.ik',
 'new_EM_D_absolute_charge_exchanged_Soma_K_Tst.ik',
 'new_EM_D_absolute_charge_exchanged_Soma_net_axial',
 'new_EM_D_absolute_charge_exchanged_Soma_i_cap',
 'new_EM_D_charge_exchanged_AIS_pas.i',
 'new_EM_D_charge_exchanged_AIS_NaTa_t.ina',
 'new_EM_D_charge_exchanged_AIS_Nap_Et2.ina',
 'new_EM_D_charge_exchanged_AIS_Ca_HVA.ica',
 'new_EM_D_charge_exchanged_AIS_Ca_LVAst.ica',
 'new_EM_D_charge_exchanged_AIS_SKv3_1.ik',
 'new_EM_D_charge_exchanged_AIS_SK_E2.ik',
 'new_EM_D_charge_exchanged_AIS_Ih.ihcn',
 'new_EM_D_charge_exchanged_AIS_Im.ik',
 'new_EM_D_charge_exchanged_AIS_K_Pst.ik',
 'new_EM_D_charge_exchanged_AIS_K_Tst.ik',
 'new_EM_D_charge_exchanged_AIS_net_axial',
 'new_EM_D_charge_exchanged_AIS_i_cap',
 'new_EM_D_absolute_charge_exchanged_AIS_pas.i',
 'new_EM_D_absolute_charge_exchanged_AIS_NaTa_t.ina',
 'new_EM_D_absolute_charge_exchanged_AIS_Nap_Et2.ina',
 'new_EM_D_absolute_charge_exchanged_AIS_Ca_HVA.ica',
 'new_EM_D_absolute_charge_exchanged_AIS_Ca_LVAst.ica',
 'new_EM_D_absolute_charge_exchanged_AIS_SKv3_1.ik',
 'new_EM_D_absolute_charge_exchanged_AIS_SK_E2.ik',
 'new_EM_D_absolute_charge_exchanged_AIS_Ih.ihcn',
 'new_EM_D_absolute_charge_exchanged_AIS_Im.ik',
 'new_EM_D_absolute_charge_exchanged_AIS_K_Pst.ik',
 'new_EM_D_absolute_charge_exchanged_AIS_K_Tst.ik',
 'new_EM_D_absolute_charge_exchanged_AIS_net_axial',
 'new_EM_D_absolute_charge_exchanged_AIS_i_cap',
 'new_EM_D_charge_exchanged_tuft_pas.i',
 'new_EM_D_charge_exchanged_tuft_NaTa_t.ina',
 'new_EM_D_charge_exchanged_tuft_Nap_Et2.ina',
 'new_EM_D_charge_exchanged_tuft_Ca_HVA.ica',
 'new_EM_D_charge_exchanged_tuft_Ca_LVAst.ica',
 'new_EM_D_charge_exchanged_tuft_SKv3_1.ik',
 'new_EM_D_charge_exchanged_tuft_SK_E2.ik',
 'new_EM_D_charge_exchanged_tuft_Ih.ihcn',
 'new_EM_D_charge_exchanged_tuft_Im.ik',
 'new_EM_D_charge_exchanged_tuft_K_Pst.ik',
 'new_EM_D_charge_exchanged_tuft_K_Tst.ik',
 'new_EM_D_charge_exchanged_tuft_net_axial',
 'new_EM_D_charge_exchanged_tuft_i_cap',
 'new_EM_D_absolute_charge_exchanged_tuft_pas.i',
 'new_EM_D_absolute_charge_exchanged_tuft_NaTa_t.ina',
 'new_EM_D_absolute_charge_exchanged_tuft_Nap_Et2.ina',
 'new_EM_D_absolute_charge_exchanged_tuft_Ca_HVA.ica',
 'new_EM_D_absolute_charge_exchanged_tuft_Ca_LVAst.ica',
 'new_EM_D_absolute_charge_exchanged_tuft_SKv3_1.ik',
 'new_EM_D_absolute_charge_exchanged_tuft_SK_E2.ik',
 'new_EM_D_absolute_charge_exchanged_tuft_Ih.ihcn',
 'new_EM_D_absolute_charge_exchanged_tuft_Im.ik',
 'new_EM_D_absolute_charge_exchanged_tuft_K_Pst.ik',
 'new_EM_D_absolute_charge_exchanged_tuft_K_Tst.ik',
 'new_EM_D_absolute_charge_exchanged_tuft_net_axial',
 'new_EM_D_absolute_charge_exchanged_tuft_i_cap',
 'new_EM_D_charge_exchanged_basal_pas.i',
 'new_EM_D_charge_exchanged_basal_NaTa_t.ina',
 'new_EM_D_charge_exchanged_basal_Nap_Et2.ina',
 'new_EM_D_charge_exchanged_basal_Ca_HVA.ica',
 'new_EM_D_charge_exchanged_basal_Ca_LVAst.ica',
 'new_EM_D_charge_exchanged_basal_SKv3_1.ik',
 'new_EM_D_charge_exchanged_basal_SK_E2.ik',
 'new_EM_D_charge_exchanged_basal_Ih.ihcn',
 'new_EM_D_charge_exchanged_basal_Im.ik',
 'new_EM_D_charge_exchanged_basal_K_Pst.ik',
 'new_EM_D_charge_exchanged_basal_K_Tst.ik',
 'new_EM_D_charge_exchanged_basal_net_axial',
 'new_EM_D_charge_exchanged_basal_i_cap',
 'new_EM_D_absolute_charge_exchanged_basal_pas.i',
 'new_EM_D_absolute_charge_exchanged_basal_NaTa_t.ina',
 'new_EM_D_absolute_charge_exchanged_basal_Nap_Et2.ina',
 'new_EM_D_absolute_charge_exchanged_basal_Ca_HVA.ica',
 'new_EM_D_absolute_charge_exchanged_basal_Ca_LVAst.ica',
 'new_EM_D_absolute_charge_exchanged_basal_SKv3_1.ik',
 'new_EM_D_absolute_charge_exchanged_basal_SK_E2.ik',
 'new_EM_D_absolute_charge_exchanged_basal_Ih.ihcn',
 'new_EM_D_absolute_charge_exchanged_basal_Im.ik',
 'new_EM_D_absolute_charge_exchanged_basal_K_Pst.ik',
 'new_EM_D_absolute_charge_exchanged_basal_K_Tst.ik',
 'new_EM_D_absolute_charge_exchanged_basal_net_axial',
 'new_EM_D_absolute_charge_exchanged_basal_i_cap',
 'new_EM_C_bifurcation_charge_exchanged_NaTa_t.ina',
 'new_EM_C_bifurcation_charge_exchanged_Ca_HVA.ica',
 'new_EM_C_bifurcation_charge_exchanged_Ca_LVAst.ica',
 'new_EM_C_bifurcation_charge_exchanged_SKv3_1.ik',
 'new_EM_C_bifurcation_charge_exchanged_SK_E2.ik',
 'new_EM_C_bifurcation_charge_exchanged_Ih.ihcn',
 'new_EM_C_bifurcation_charge_exchanged_Im.ik',
 'new_EM_C_bifurcation_charge_exchanged_pas.i',
 'new_EM_C_bifurcation_charge_exchanged_i_cap',
 'new_EM_C_bifurcation_charge_exchanged_current_from_prox',
 'new_EM_C_bifurcation_charge_exchanged_current_from_dist',
 'new_EM_C_bifurcation_charge_exchanged_net_axial']

### code to record energy metrics ###

def interp_out(t, out, tmin = None, tmax = None):
    select = (t > tmin) & (t < tmax)
    t_new = np.array([tmin] + list(t[select]) + [tmax])
    out_ = {}
    for k,v in out.items():
        out_[k] = np.interp(t_new,t,v)
    return t_new, out_



def energy_metric_axial_depo_fraction(cell):
    out = {}
    sec = get_main_bifurcation_section(cell)
    seg = [seg for seg in sec][-1]
    out.update(get_current_membrane_current(sec,-1, mode = 'current_density'))
    out.update(get_axial_current(sec,-1, mode = 'current_density'))
    sum_ = 0
    t = np.array(cell.tVec)
    t, out = interp_out(t, out, tmin = 295, tmax = 295+60)
    for k in out.keys():
        if k in ['i_cap', 'current_from_prox', 'current_from_dist', 'net_axial']:
            continue
        x = out[k][:]
    # and now save the hyperpolarizing currents
    sum_hyper = 0 
    for k in out.keys():
        if k in ['i_cap', 'current_from_prox', 'current_from_dist', 'net_axial']:
            continue
        x = out[k][:]
        y = x.copy() # save hyperpolarizing currents
        y[y<0] = 0
        x[x>0] = 0 # throw out all hyperpolarizing currents
        hyp_integral = trapz(np.abs(y), x = t)
        sum_hyper += hyp_integral    
        integral = trapz(np.abs(x), x = t)
        sum_ += integral
    axial_integral = trapz(np.abs(out['net_axial']), x = t)
    cap_integral = trapz(np.abs(out['i_cap']), x = t)
    return {'new_EM_A_bifurcation_axial_integral_frac':axial_integral/sum_, 
            #'new_EM_bifurcation_A_capacitative_integral_frac':cap_integral/sum_, 
            'new_EM_A_bifurcation_depolarizing_membrane_current_integral':sum_, 
            'new_EM_A_bifurcation_hyperpolarizing_membrane_current_integral':sum_hyper,
            #'new_EM_bifurcation_A_segment_area': seg.area()
           }



def energy_metric_overlap(cell):
    sec = get_main_bifurcation_section(cell)
    seg = [seg for seg in sec][-1]
    out = get_current_membrane_current(sec,-1, mode = 'current_density')
    range_vars  = ['pas.i', 'NaTa_t.ina', 'Ca_HVA.ica', 'Ca_LVAst.ica', 'SKv3_1.ik', 'SK_E2.ik', 'Ih.ihcn', 'Im.ik']
    t,bd,bh = area_plot_dict(cell.tVec, out, range_vars, colormap, 295,295+60, ax = 'no')
    overlap = np.min([bh, bd*-1], axis = 0)
    return {'new_EM_B_bifurcation_overlap': trapz(overlap, x = t)}



def energy_metric_charge_exchanged_HZ(cell):
    out = {}
    sec = get_main_bifurcation_section(cell)
    seg = [seg for seg in sec][-1]
    out.update(get_current_membrane_current(sec,-1, mode = 'current_density'))
    out.update(get_axial_current(sec,-1, mode = 'current_density'))
    t = np.array(cell.tVec)
    t, out = interp_out(t, out, tmin = 295, tmax = 295+60)
    return {'new_EM_C_bifurcation_charge_exchanged_' + k: trapz(np.abs(out[k]), x = t) for k in out}



def energy_metric_charge_exchanged_by_subcellular_compartment(cell):
    augment_cell_with_detailed_labels(cell)
    out_ = {}
    for label in set(sec.label_detailed for sec in cell.sections):
        out = get_total_current_detailed(cell, sec_label_filter = [label])
        t = np.array(cell.tVec)
        t, out = interp_out(t, out, tmin = 295, tmax = 295+60)
        dummy = {'new_EM_D_charge_exchanged_' + label + '_' + k: trapz(out[k], x = t) for k in out}
        out_.update(dummy)
        dummy = {'new_EM_D_absolute_charge_exchanged_' + label + '_' + k: trapz(np.abs(out[k]), x = t) for k in out}
        out_.update(dummy)
    return out_



def energy_metric_soma_vs_dend(cell):
    out_ = {}
#     augment_cell_with_detailed_labels(cell)
    t = np.array(cell.tVec)
    out_soma = get_total_current(cell, sec_label_filter = ['Soma'])
    out_dend = get_total_current(cell, sec_label_filter = ['Dendrite', 'ApicalDendrite'])
    t_interp, out_soma_interp = interp_out(t, out_soma, tmin = 295, tmax = 295+60)
    t_interp, out_dend_interp = interp_out(t, out_dend, tmin = 295, tmax = 295+60)
    range_vars  = ['pas.i', 'NaTa_t.ina', 'Ca_HVA.ica', 'Ca_LVAst.ica', 'SKv3_1.ik', 'SK_E2.ik', 'Ih.ihcn', 'Im.ik']
    t2,bd_soma,_ = area_plot_dict(t_interp, out_soma_interp, range_vars, colormap, 295,295+60, ax = 'no')
    t2,bd_dend,_ = area_plot_dict(t_interp, out_dend_interp, range_vars, colormap, 295,295+60, ax = 'no')
    assert len(t2) == len(t_interp)
    return {'new_EM_E_depo_charge_exchanged_dend_vs_soma': trapz(bd_dend, x = t2) / trapz(bd_soma, x = t2)}



def get_all_energy_metrics(cell):
    out = {}
    out.update(energy_metric_axial_depo_fraction(cell))
    out.update(energy_metric_overlap(cell))
    out.update(energy_metric_soma_vs_dend(cell))
    out.update(energy_metric_charge_exchanged_by_subcellular_compartment(cell))
    out.update(energy_metric_charge_exchanged_HZ(cell))
    return out


def get_all_energy_metrics_from_p(simulator, parameters):
    p = parameters
    s = simulator
    cell,p = s.get_simulated_cell(p, 'BAC', simulate = False) 
    for rv in ['NaTa_t.ina','Ca_HVA.ica','Ca_LVAst.ica',
               'SKv3_1.ik','SK_E2.ik','Ih.ihcn',
               'Im.ik','Nap_Et2.ina','K_Pst.ik',
               'K_Tst.ik','pas.i','i_cap']:
        cell.record_range_var(rv)
    I.scp.init_neuron_run(I.scp.NTParameterSet({'tStop': 295+100, 'dt': 0.025, 'T': 34, 'Vinit': -75}), vardt = True)
    return get_all_energy_metrics(cell)


### code to for energy related calculations from the newly recorded new energy metrics ###


def return_charge_calculations(df): 
    '''needs df with new energy metrics'''
    
    out = {}
    dep = df['new_EM_A_bifurcation_depolarizing_membrane_current_integral']
    hyp = df['new_EM_A_bifurcation_hyperpolarizing_membrane_current_integral']
    axial = df['new_EM_C_bifurcation_charge_exchanged_net_axial']
    LVA = df['new_EM_C_bifurcation_charge_exchanged_Ca_LVAst.ica']
    HVA = df['new_EM_C_bifurcation_charge_exchanged_Ca_HVA.ica']
    
    out['new_EM_G_hyperpolarizing_as_fraction_of_depolarizing'] = hyp/dep
    out['new_EM_G_axial_as_a_fraction_of_CaLVA'] = axial/LVA
    out['new_EM_G_axial_as_a_fraction_of_CaHVA'] = axial/HVA
    
    return out


def energy_metric_ATP_HZ(df):
    '''needs df with parameters and new energy metrics (for charge)'''
    out = {}
    unit_factor = 1e-12 #(from pC to C)
    N_A = scipy.constants.N_A
    F = scipy.constants.physical_constants['Faraday constant'][0]

    q_Ca_LVA = df['new_EM_C_bifurcation_charge_exchanged_Ca_LVAst.ica']
    q_Ca_HVA = df['new_EM_C_bifurcation_charge_exchanged_Ca_HVA.ica']
    q_Na = df['new_EM_C_bifurcation_charge_exchanged_NaTa_t.ina'] 
    q_Ih = df['new_EM_C_bifurcation_charge_exchanged_Ih.ihcn']

    out['new_EM_F_bifurcation_ATP_Ca_density'] = N_A/(2*F) * (q_Ca_HVA + q_Ca_LVA) * unit_factor
    out['new_EM_F_bifurcation_ATP_Na_density'] = N_A/(3*F) * (q_Na) * unit_factor  
    out['new_EM_F_bifurcation_ATP_Ih_density'] = N_A/(3*F) * (q_Ih) * unit_factor  
    
    return out 


def total_charge_exchanged_all_compartments(df): 
    out = {}
    rows = []
    for current in membrane_currents: 
        # exclude axial and capacitive currents 
        if current in ['net_axial', 'i_cap']:
            continue 
        rows = rows + find_label(new_energy_metrics, ['absolute', current])
    out['total_current'] = df[rows].sum(axis = 1)
    return out



def energy_metric_ATP_all_compartments(df):
    '''needs df with parameters and new energy metrics (for charge) '''
    out = {}
    
    N_A = scipy.constants.N_A
    F = scipy.constants.physical_constants['Faraday constant'][0]
    unit_factor = 1e-12 #(from pC to C)

    q_Ca_LVA = df[find_label(new_energy_metrics, ['absolute', 'Ca_LVA'])].sum(axis = 1)
    q_Ca_HVA = df[find_label(new_energy_metrics, ['absolute', 'Ca_HVA'])].sum(axis = 1)
    q_Na = df[find_label(new_energy_metrics, ['absolute', 'Na'])].sum(axis = 1)
    q_Ih = df[find_label(new_energy_metrics, ['absolute', 'Ih'])].sum(axis = 1)
    
    out['new_EM_F_all_compartments_ATP_Ca'] = N_A/(2*F) * (q_Ca_HVA + q_Ca_LVA) * unit_factor
    out['new_EM_F_all_compartments_ATP_Na'] = N_A/(3*F) * (q_Na) * unit_factor
    out['new_EM_F_all_compartments_ATP_Ih'] = N_A/(3*F) * (q_Ih) * unit_factor
    
    out['new_EM_F_all_compartments_ATP_total'] = (out['new_EM_F_all_compartments_ATP_Ca'] +\
                                                    out['new_EM_F_all_compartments_ATP_Na']) +\
                                                    out['new_EM_F_all_compartments_ATP_Ih']
    
    return out 



def energy_metric_ATP_apical_dendrite(df):
    '''needs df with parameters and new energy metrics (for charge) '''
    out = {}
    
    N_A = scipy.constants.N_A
    F = scipy.constants.physical_constants['Faraday constant'][0]
    unit_factor = 1e-12 #(from pC to C)
    
    # to get the total, add trunk, tuft and oblique 
    all_apical_labels = ['trunk' ,'oblique' ,'tuft']
    energy_metric_cat = 'new_EM_D_absolute_charge_exchanged'
    na_channels = ['NaTa_t.ina', 'Nap_Et2.ina']
    
    
    q_Ca_LVA = df[['_'.join([energy_metric_cat, label, 'Ca_LVAst.ica']) 
                   for label in all_apical_labels]].sum(axis = 1)
        
    q_Ca_HVA = df[['_'.join([energy_metric_cat, label, 'Ca_HVA.ica']) 
                   for label in all_apical_labels]].sum(axis = 1)
    
    q_Na = df[['_'.join([energy_metric_cat, label, na_chan]) 
                   for label in all_apical_labels for na_chan in na_channels]].sum(axis = 1)
    
    q_Ih = df[['_'.join([energy_metric_cat, label, 'Ih.ihcn']) 
                   for label in all_apical_labels]].sum(axis = 1)
    
    out['new_EM_F_apical_ATP_Ca'] = N_A/(2*F) * (q_Ca_HVA + q_Ca_LVA) * unit_factor
    out['new_EM_F_apical_ATP_Na'] = N_A/(3*F) * (q_Na) * unit_factor
    out['new_EM_F_apical_ATP_Ih'] = N_A/(3*F) * (q_Ih) * unit_factor

    out['new_EM_F_apical_ATP_total'] = (out['new_EM_F_apical_ATP_Ca'] + out['new_EM_F_apical_ATP_Na'])
    return out 



# perisomatic: includes soma and axon
def energy_metric_ATP_soma(df):
    '''needs df with parameters and new energy metrics (for charge) '''
    out = {}
    
    N_A = scipy.constants.N_A
    F = scipy.constants.physical_constants['Faraday constant'][0]
    unit_factor = 1e-12 #(from pC to C)

    all_perisomatic_labels = ['Soma', 'AIS']
    energy_metric_cat = 'new_EM_D_absolute_charge_exchanged'
    na_channels = ['NaTa_t.ina', 'Nap_Et2.ina']
    
    q_Ca_LVA = df[['_'.join([energy_metric_cat, label, 'Ca_LVAst.ica']) 
                   for label in all_perisomatic_labels]].sum(axis = 1)
    q_Ca_HVA = df[['_'.join([energy_metric_cat, label, 'Ca_HVA.ica']) 
                   for label in all_perisomatic_labels]].sum(axis = 1)
    q_Na =  df[['_'.join([energy_metric_cat, label, na_chan]) 
                   for label in all_perisomatic_labels for na_chan in na_channels]].sum(axis = 1)
    q_Ih =  df[['_'.join([energy_metric_cat, label, 'Ih.ihcn']) 
                   for label in all_perisomatic_labels]].sum(axis = 1)

    out['new_EM_F_perisomatic_ATP_Ca'] = N_A/(2*F) * (q_Ca_HVA + q_Ca_LVA) * unit_factor
    out['new_EM_F_perisomatic_ATP_Na'] = N_A/(3*F) * (q_Na) * unit_factor
    out['new_EM_F_perisomatic_ATP_Ih'] = N_A/(3*F) * (q_Ih) * unit_factor
    out['new_EM_F_perisomatic_ATP_total'] = (out['new_EM_F_perisomatic_ATP_Ca'] +\
                                             out['new_EM_F_perisomatic_ATP_Na'] +\
                                              out['new_EM_F_perisomatic_ATP_Ih']) 
    
    return out 



def return_charge_related_calculations_and_ATP(df): 
    '''needs df_row with parameters and new energy metrics (for charge) '''
    out = {}
    out.update(energy_metric_ATP_HZ(df))
    out.update(energy_metric_ATP_apical_dendrite(df))
    out.update(energy_metric_ATP_soma(df))
    out.update(energy_metric_ATP_all_compartments(df))
    out.update(total_charge_exchanged_all_compartments(df))
    out.update(return_charge_calculations(df))
    return out 