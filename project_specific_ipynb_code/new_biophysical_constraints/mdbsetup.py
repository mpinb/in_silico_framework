'''Usage: import this module, set CHIRP, CRITFREQ, STEP, HYPERPOLARIZING, and call the init method with the model data base that you want to initiailze'''
import Interface as I

import os
from functools import partial
from copy import deepcopy
import numpy as np
import single_cell_parser as scp

import biophysics_fitting.hay_complete_default_setup
import biophysics_fitting.hay_complete_default_setup_python
from biophysics_fitting import hay_evaluation_python
from biophysics_fitting.hay_complete_default_setup_python import interpolate_vt, Evaluator, merge, map_truefalse_to_str
from biophysics_fitting.hay_evaluation import hay_evaluate_StepOne, hay_evaluate_StepTwo, hay_evaluate_StepThree
from biophysics_fitting.utils import execute_in_child_process_kept_alive
from biophysics_fitting.combiner import Combiner
import project_specific_ipynb_code.hot_zone
from biophysics_fitting.utils import execute_in_child_process
import biophysics_fitting.hay_complete_default_setup_python
from biophysics_fitting import hay_complete_default_setup
from biophysics_fitting.utils import get_inner_sec_dist_dict as get_inner_sec_dist_list
from biophysics_fitting.utils import get_inner_section_at_distance
from biophysics_fitting import hay_complete_default_setup_python

from project_specific_ipynb_code.new_biophysical_constraints import crit_freq
from project_specific_ipynb_code.new_biophysical_constraints import chirp
from project_specific_ipynb_code.new_biophysical_constraints import hyperpolarizing
from project_specific_ipynb_code.biophysical_models import modify_simulator_to_record_apical_dendrite_conductances

from project_specific_ipynb_code.hot_zone import get_cell_object_from_hoc

morphology_dir = os.path.dirname(__file__)
morphology_dir = os.path.join(morphology_dir, 'morphologies')

def set_globals(CHIRP_ = None, CRITFREQ_ = None, STEP_ = None, HYPERPOLARIZING_ = None, PARAMETERS_ = None, SCALE_COMPARTMENT = None):
    global CHIRP,CRITFREQ,STEP,HYPERPOLARIZING,params,get_template
    CHIRP = CHIRP_
    CRITFREQ = CRITFREQ_
    STEP = STEP_
    HYPERPOLARIZING = HYPERPOLARIZING_
    
    if PARAMETERS_ == 3:
        params = params_v3
        get_template = partial(get_template_v3, compartment = SCALE_COMPARTMENT)
    elif PARAMETERS_ == 4:
        params = params_v4
        get_template = partial(get_template_v4, compartment = SCALE_COMPARTMENT)
    else:
        raise NotImplementedError()
    
def init(mdb, CHIRP_ = None, CRITFREQ_ = None, STEP_ = None, HYPERPOLARIZING_ = None, PARAMETERS_ = None, SCALE_COMPARTMENT = None):
    '''
    CHIRP_: True / False
    CRITFREQ_: True / False
    STEP_: STEP_
    HYPERPOLARIZING_: 
    PARAMETERS_: integer, 1 to 4
            # template v2: new Ca buffer
            # template v3: new Ca buffer, capped exponential Ih
            # template v4: new Ca buffer, capped exponential Ih, capped linear NaTa_t
    SCALE: 'ApicalDendrite' or 'Trunk'
    '''
    
    set_globals(CHIRP_, CRITFREQ_, STEP_, HYPERPOLARIZING_, PARAMETERS_, SCALE_COMPARTMENT)

    mdb.create_managed_folder('morphology', raise_ = False)
    path = '/gpfs/soma_fs/scratch/abast/results/20220126_compile_modeldb_code_for_energy_paper/morphology/'
    
    selection = [
         '89_L5_CDK20050712_nr6L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '90_L5_CDK20050720_nr7L5B_dend_PC_neuron_transform_registered_C2.hoc',
         'WR69_Cell2_L5TT.hoc',
         '88_L5_CDK20050707_nr5L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '93_L5_CDK20060808_nr10L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '84_L5_CDK20050929_nr1L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '87_L5_CDK20050131_nr4L5B_ID14_dend_PC_neuron_transform_registered_C2.hoc',
         'WR64_Cell8_L5TT_C2-registered.hocwith_radius_constant_mean.hoc',
         '85_L5_CDK20041206_nr2L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '91_L5_CDK20050815_nr8L5B_dend_PC_neuron_transform_registered_C2.hoc',
         'WR71_Cell6_L5TT_C2-registered.hocwith_radius_constant_mean_Soma.hoc']
    
    naming_dict = {
         '89': '89_L5_CDK20050712_nr6L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '90': '90_L5_CDK20050720_nr7L5B_dend_PC_neuron_transform_registered_C2.hoc',
         'WR69': 'WR69_Cell2_L5TT.hoc',
         '88': '88_L5_CDK20050707_nr5L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '93': '93_L5_CDK20060808_nr10L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '84': '84_L5_CDK20050929_nr1L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '87': '87_L5_CDK20050131_nr4L5B_ID14_dend_PC_neuron_transform_registered_C2.hoc',
         # 'WR64_Cell8_L5TT_medfilt.hoc',
         'WR64': 'WR64_Cell8_L5TT_C2-registered.hocwith_radius_constant_mean.hoc',
         '85': '85_L5_CDK20041206_nr2L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '86': '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2.hoc',
         '91': '91_L5_CDK20050815_nr8L5B_dend_PC_neuron_transform_registered_C2.hoc',
         'WR71': 'WR71_Cell6_L5TT_C2-registered.hocwith_radius_constant_mean_Soma.hoc'}
    
    for f in selection:
        I.shutil.copy(I.os.path.join(morphology_dir, f), mdb['morphology'])
    
    for name in naming_dict:
        if not name in mdb.keys():
            mdb.create_sub_mdb(name) 
        m = mdb[name]
        hocpath = mdb['morphology'].join(naming_dict[name])
        cell = get_cell_object_from_hoc(hocpath)
        m['fixed_params'] = get_fixed_params_from_cell(cell)
        m['get_fixed_params'] = get_fixed_params
        if not 'morphology' in m.keys():
            m.create_managed_folder('morphology')
            I.shutil.copy(hocpath, m['morphology'])
        m.setitem('params', params, dumper = I.dumper_pandas_to_pickle)
        m.setitem('get_Simulator', I.partial(get_Simulator_mdb, delay = 300), dumper = I.dumper_to_cloudpickle)
        m.setitem('get_Evaluator', I.partial(get_Evaluator_mdb, delay = 300.), dumper = I.dumper_to_cloudpickle)
        m.setitem('get_Combiner', I.partial(get_Combiner_mdb), dumper = I.dumper_to_cloudpickle)
        
# template v2: new Ca buffer
# template v3: new Ca buffer, capped exponential Ih
# template v4: new Ca buffer, capped exponential Ih, capped linear NaTa_t

def scale_apical(cell_param, params):
    assert(len(params) == 1)
    cell_param.cell_modify_functions.scale_apical.scale = params['scale']
    return cell_param

def get_fixed_params(mdb_setup):
    fixed_params = mdb_setup['fixed_params']
    fixed_params['morphology.filename'] = mdb_setup['morphology'].get_file('hoc')
    return fixed_params

def make_sure_hay_evaluator_did_not_run():
    import biophysics_fitting.hay_evaluation
    assert biophysics_fitting.hay_evaluation.is_setup() == False
    
def import_Interface_first(fun):
    def helper(*args, **kwargs):
        import Interface
        return fun(*args, **kwargs)
    return helper

def get_Simulator_mdb(mdb_setup, delay = None):
    fixed_params = mdb_setup['get_fixed_params'](mdb_setup)
    fixed_params['BAC.stim.delay'] = [295, 295+delay]
    fixed_params['BAC.run.tStop'] = 600+delay    
    # s = hay_complete_default_setup_python.get_Simulator(I.pd.Series(fixed_params), step = step)
    if STEP:
        s = hay_complete_default_setup.get_Simulator(I.pd.Series(fixed_params), step = True)
    else:
        s = hay_complete_default_setup.get_Simulator(I.pd.Series(fixed_params), step = False)   
    s.setup.check_funs.append(make_sure_hay_evaluator_did_not_run)        
    s.setup.cell_param_generator = get_template
    s.setup.cell_param_modify_funs.append(('scale_apical', scale_apical))
    if CRITFREQ:
        crit_freq.modify_simulator_to_run_crit_freq_stimuli(s, delay = 300, tStop = 700, n_stim = 4,
                                                             freq_list = [35, 50, 100, 150, 200],
                                                             amplitude = 4, duration = 2)
    if CHIRP:
        chirp.modify_simulator_to_run_chirp_stimuli(s, delay = 300, duration = 10000, final_freq = 20, dist = 400)
        
    if HYPERPOLARIZING:
        hyperpolarizing.modify_simulator_to_run_hyperpolarizing_stimuli(s,
                                                                        duration = 1000, 
                                                                        amplitude = -0.05, 
                                                                        delay = 1000,
                                                                        dist = 400)
        
        hyperpolarizing.modify_simulator_to_run_dend_hyperpolarizing_stimuli(s, 
                                                                             duration = 1000, 
                                                                             delay = 1000, 
                                                                             amplitude = -0.05, 
                                                                             dist = 400)
    
    
        
    # modify_simulator_to_record_apical_dendrite_conductances(s)
    
    return s

def update(old_function, update_function):
    def get_Simulator(mdb):
        obj = old_function(mdb)
        update_function(obj)
        return obj
    return get_Simulator

def remove_from_vt(tVec, vList, tstart, tend, shift = 0):
    mask = (tVec < tstart) | (tVec > tend) 
    tVec = tVec[mask]
    vList = [v[mask] for v in vList]
    return tVec + shift, vList

def cut_from_vt(tVec, vList, tstart, tend, shift = 0):
    mask = (tVec < tstart) | (tVec > tend) 
    tVec[tVec > tend] = tVec[tVec > tend] - tend + tstart
    tVec = tVec[mask]
    vList = [v[mask] for v in vList]
    return tVec , vList

# first burst
def prepare_vt_to_select_one_burst(vt, delay = None):
    # 20230919 make sure this prefun does not throw an error if BAC has not been simulated
    if not 'BAC.hay_measure' in vt: 
        return vt
    
    vt_new = deepcopy(vt)
    t, (v1,v2) = cut_from_vt(deepcopy(vt_new['BAC.hay_measure']['tVec']), 
                             deepcopy(vt_new['BAC.hay_measure']['vList']), 
                             295+delay, 600+delay)
    vt_new['BAC1.hay_measure'] = {}
    vt_new['BAC1.hay_measure']['tVec'] = t
    vt_new['BAC1.hay_measure']['vList'] = [v1,v2]

    t, (v1,v2) = remove_from_vt(deepcopy(vt['BAC.hay_measure']['tVec']), 
                                deepcopy(vt['BAC.hay_measure']['vList']), 
                                295, 295+delay, shift = -delay)
    vt_new['BAC2.hay_measure'] = {}
    vt_new['BAC2.hay_measure']['tVec'] = t
    vt_new['BAC2.hay_measure']['vList'] = [v1,v2]
    
    del vt_new['BAC.hay_measure']
    
    return vt_new

def get_Evaluator(interpolate_voltage_trace = True, delay = None):
    e = Evaluator()
    bap = hay_evaluation_python.bAP()
    bac1 = hay_evaluation_python.BAC(prefix = '1')
    bac2 = hay_evaluation_python.BAC(prefix = '2')

    if interpolate_voltage_trace:
        e.setup.pre_funs.append(partial(prepare_vt_to_select_one_burst, delay = delay))
        e.setup.pre_funs.append(interpolate_vt)        
        
    e.setup.evaluate_funs.append(['BAC1.hay_measure', 
                                  bac1.get,
                                  'BAC1.hay_features'])
    
    e.setup.evaluate_funs.append(['BAC2.hay_measure', 
                                  bac2.get,
                                  'BAC2.hay_features'])
    
    e.setup.evaluate_funs.append(['bAP.hay_measure',
                                  bap.get,
                                  'bAP.hay_features'])
    
    if STEP:
        e.setup.evaluate_funs.append(['StepOne.hay_measure',
                                         execute_in_child_process_kept_alive(import_Interface_first(hay_evaluate_StepOne)),
                                         #hay_evaluate_StepOne,
                                         'StepOne.hay_features'])
        e.setup.evaluate_funs.append(['StepTwo.hay_measure',
                                         execute_in_child_process_kept_alive(import_Interface_first(hay_evaluate_StepTwo)),
                                         #hay_evaluate_StepTwo,
                                         'StepTwo.hay_features'])
        e.setup.evaluate_funs.append(['StepThree.hay_measure',
                                        execute_in_child_process_kept_alive(import_Interface_first(hay_evaluate_StepThree)),
                                        #hay_evaluate_StepThree,
                                        'StepThree.hay_features'])

    e.setup.finalize_funs.append(lambda x: merge(list(x.values()))) 
    # e.setup.finalize_funs.append(map_truefalse_to_str)    
    
    if CRITFREQ:
        crit_freq.modify_evaluator_to_evaluate_crit_freq_stimuli(e, 
                                                                 freq_list = [35, 50, 100, 150, 200],
                                                                 delay = 300, n_stim = 4, soma_threshold = 0)
    if CHIRP:
        chirp.modify_evaluator_to_evaluate_chirp_stimuli(e, delay = 300, duration = 10000)
        
    if HYPERPOLARIZING:
        hyperpolarizing.modify_evaluator_to_evaluate_hyperpolarizing_stimuli(e)
    
    return e

def get_Evaluator_mdb(mdb_setup, delay = None):
    return get_Evaluator(delay = delay)

def get_Combiner():
    c = Combiner()
    c.setup.append('bAP_somatic_spike', ['bAP_APwidth', 'bAP_APheight', 'bAP_spikecount'])
    c.setup.append('bAP', ['bAP_att2', 'bAP_att3'])
    c.setup.append('1BAC_somatic', ['1BAC_ahpdepth', '1BAC_APheight', '1BAC_ISI'])
    c.setup.append('1BAC_caSpike', ['1BAC_caSpike_height', '1BAC_caSpike_width'])
    c.setup.append('1BAC_spikecount', ['1BAC_spikecount'])
    c.setup.append('2BAC_somatic', ['2BAC_ahpdepth', '2BAC_APheight', '2BAC_ISI'])
    c.setup.append('2BAC_caSpike', ['2BAC_caSpike_height', '2BAC_caSpike_width'])
    c.setup.append('2BAC_spikecount', ['2BAC_spikecount'])    
    if STEP: 
        c.setup.append('step_mean_frequency', ['mf1', 'mf2', 'mf3'])
        c.setup.append('step_AI_ISIcv', ['AI1', 'AI2', 'ISIcv1', 'ISIcv2', 'AI3', 'ISIcv3'])
        # c.setup.append('step_doublet_ISI', ['DI1', 'DI2'])
        c.setup.append('step_doublet_ISI', ['DI1', 'DI2', 'DI3'])
        c.setup.append('step_AP_height', ['APh1', 'APh2', 'APh3'])
        c.setup.append('step_time_to_first_spike', ['TTFS1', 'TTFS2', 'TTFS3'])
        c.setup.append('step_AHP_depth', ['fAHPd1', 'fAHPd2', 'fAHPd3', 'sAHPd1', 'sAHPd2', 'sAHPd3'])
        c.setup.append('step_AHP_slow_time', ['sAHPt1', 'sAHPt2', 'sAHPt3'])
        c.setup.append('step_AP_width', ['APw1', 'APw2', 'APw3'])
    if CRITFREQ:
        crit_freq.modify_combiner_to_add_crit_freq_error(c, freq_list = [35, 50, 100, 150, 200])
    if CHIRP:
        chirp.modify_combiner_to_add_chirp_error(c)
    if HYPERPOLARIZING:
        hyperpolarizing.modify_combiner_to_add_hyperpolarizing_stimuli_error(c)
    c.setup.combinefun = np.max
    return c

def get_Combiner_mdb(mdb_setup):
    return get_Combiner()

def get_fixed_params_from_cell(cell):
    bifur = get_bifurcation_distance(cell)
    outsidescale_sections = get_outsidescale_sections(cell)
    return {'BAC.hay_measure.recSite': bifur - 10 - 180,
      'BAC.stim.dist': bifur - 10 - 180,
      'bAP.hay_measure.recSite1':bifur - 10 - 180,
      'bAP.hay_measure.recSite2':bifur - 10,
      'crit_freq.hay_measure.recSite1':bifur - 10 - 180, 
      'crit_freq.hay_measure.recSite2':bifur - 10,
      'crit_freq1.hay_measure.recSite1':bifur - 10 - 180, 
      'crit_freq1.hay_measure.recSite2':bifur - 10,         
      'crit_freq2.hay_measure.recSite1':bifur - 10 - 180, 
      'crit_freq2.hay_measure.recSite2':bifur - 10,  
      'crit_freq3.hay_measure.recSite1':bifur - 10 - 180, 
      'crit_freq3.hay_measure.recSite2':bifur - 10,
      'crit_freq4.hay_measure.recSite1':bifur - 10 - 180, 
      'crit_freq4.hay_measure.recSite2':bifur - 10,
      'crit_freq5.hay_measure.recSite1':bifur - 10 - 180, 
      'crit_freq5.hay_measure.recSite2':bifur - 10,
#       'chirp.hay_measure.recSite1':bifur - 10 - 180, 
      'chirp.hay_measure.recSite2':bifur - 10,
#       'chirp_dend.hay_measure.recSite1':bifur - 10 - 180, 
      'chirp_dend.hay_measure.recSite2':bifur - 10,
      'hot_zone.min_': bifur - 100,
      'hot_zone.max_': bifur + 100,
      'hot_zone.outsidescale_sections': outsidescale_sections,
      'morphology.filename': cell.hoc_path}

def get_bifurcation_distance(cell):
    d = project_specific_ipynb_code.hot_zone.Dendrogram(cell)
    d._compute_main_bifurcation_section()
    return d.main_bifur_dist
    
def get_outsidescale_sections(cell):
    inner_sections = get_inner_sec_dist_list(cell)
    outside_scale_sections = [lv for lv, sec in enumerate(cell.sections) 
                              if sec.label == 'ApicalDendrite' and sec not in inner_sections.values()]
    return outside_scale_sections

params_v3 = {'min': {'ephys.CaDynamics_E2_v2.apic.decay': 20.0, 'ephys.CaDynamics_E2_v2.apic.gamma': 0.0005, 'ephys.CaDynamics_E2_v2.axon.decay': 20.0, 'ephys.CaDynamics_E2_v2.axon.gamma': 0.0005, 'ephys.CaDynamics_E2_v2.soma.decay': 20.0, 'ephys.CaDynamics_E2_v2.soma.gamma': 0.0005, 'ephys.Ca_HVA.apic.gCa_HVAbar': 0.0, 'ephys.Ca_HVA.axon.gCa_HVAbar': 0.0, 'ephys.Ca_HVA.soma.gCa_HVAbar': 0.0, 'ephys.Ca_LVAst.apic.gCa_LVAstbar': 0.0, 'ephys.Ca_LVAst.axon.gCa_LVAstbar': 0.0, 'ephys.Ca_LVAst.soma.gCa_LVAstbar': 0.0, 'ephys.Ih.apic.linScale': 1.5, 'ephys.Ih.apic.max_g': 0.003, 'ephys.Im.apic.gImbar': 0.0, 'ephys.K_Pst.axon.gK_Pstbar': 0.0, 'ephys.K_Pst.soma.gK_Pstbar': 0.0, 'ephys.K_Tst.axon.gK_Tstbar': 0.0, 'ephys.K_Tst.soma.gK_Tstbar': 0.0, 'ephys.NaTa_t.apic.gNaTa_tbar': 0.0, 'ephys.NaTa_t.axon.gNaTa_tbar': 0.0, 'ephys.NaTa_t.soma.gNaTa_tbar': 0.0, 'ephys.Nap_Et2.axon.gNap_Et2bar': 0.0, 'ephys.Nap_Et2.soma.gNap_Et2bar': 0.0, 'ephys.SK_E2.apic.gSK_E2bar': 0.0, 'ephys.SK_E2.axon.gSK_E2bar': 0.0, 'ephys.SK_E2.soma.gSK_E2bar': 0.0, 'ephys.SKv3_1.apic.gSKv3_1bar': 0.0, 'ephys.SKv3_1.apic.offset': 0.0, 'ephys.SKv3_1.apic.slope': -3.0, 'ephys.SKv3_1.axon.gSKv3_1bar': 0.0, 'ephys.SKv3_1.soma.gSKv3_1bar': 0.0, 'ephys.none.apic.g_pas': 3e-05, 'ephys.none.axon.g_pas': 2e-05, 'ephys.none.dend.g_pas': 3e-05, 'ephys.none.soma.g_pas': 2e-05, 'scale_apical.scale': 0.5}, 'max': {'ephys.CaDynamics_E2_v2.apic.decay': 200.0, 'ephys.CaDynamics_E2_v2.apic.gamma': 0.05, 'ephys.CaDynamics_E2_v2.axon.decay': 1000.0, 'ephys.CaDynamics_E2_v2.axon.gamma': 0.05, 'ephys.CaDynamics_E2_v2.soma.decay': 1000.0, 'ephys.CaDynamics_E2_v2.soma.gamma': 0.05, 'ephys.Ca_HVA.apic.gCa_HVAbar': 0.005, 'ephys.Ca_HVA.axon.gCa_HVAbar': 0.001, 'ephys.Ca_HVA.soma.gCa_HVAbar': 0.001, 'ephys.Ca_LVAst.apic.gCa_LVAstbar': 0.2, 'ephys.Ca_LVAst.axon.gCa_LVAstbar': 0.01, 'ephys.Ca_LVAst.soma.gCa_LVAstbar': 0.01, 'ephys.Ih.apic.linScale': 10.0, 'ephys.Ih.apic.max_g': 0.015, 'ephys.Im.apic.gImbar': 0.001, 'ephys.K_Pst.axon.gK_Pstbar': 1.0, 'ephys.K_Pst.soma.gK_Pstbar': 1.0, 'ephys.K_Tst.axon.gK_Tstbar': 0.1, 'ephys.K_Tst.soma.gK_Tstbar': 0.1, 'ephys.NaTa_t.apic.gNaTa_tbar': 0.04, 'ephys.NaTa_t.axon.gNaTa_tbar': 4.0, 'ephys.NaTa_t.soma.gNaTa_tbar': 4.0, 'ephys.Nap_Et2.axon.gNap_Et2bar': 0.01, 'ephys.Nap_Et2.soma.gNap_Et2bar': 0.01, 'ephys.SK_E2.apic.gSK_E2bar': 0.01, 'ephys.SK_E2.axon.gSK_E2bar': 0.1, 'ephys.SK_E2.soma.gSK_E2bar': 0.1, 'ephys.SKv3_1.apic.gSKv3_1bar': 0.04, 'ephys.SKv3_1.apic.offset': 1.0, 'ephys.SKv3_1.apic.slope': 0.0, 'ephys.SKv3_1.axon.gSKv3_1bar': 2.0, 'ephys.SKv3_1.soma.gSKv3_1bar': 2.0, 'ephys.none.apic.g_pas': 0.0001, 'ephys.none.axon.g_pas': 5e-05, 'ephys.none.dend.g_pas': 0.0001, 'ephys.none.soma.g_pas': 5.02e-05, 'scale_apical.scale': 3.0}}


def get_template_v3(compartment = None):
    parameter_template = {'AIS': {'mechanisms': {'global': {},
   'range': {'CaDynamics_E2_v2': {'decay': None,
     'gamma': None,
     'spatial': 'uniform'},
    'Ca_HVA': {'gCa_HVAbar': None, 'spatial': 'uniform'},
    'Ca_LVAst': {'gCa_LVAstbar': None, 'spatial': 'uniform'},
    'Ih': {'gIhbar': 8e-05, 'spatial': 'uniform'},
    'K_Pst': {'gK_Pstbar': None, 'spatial': 'uniform'},
    'K_Tst': {'gK_Tstbar': None, 'spatial': 'uniform'},
    'NaTa_t': {'gNaTa_tbar': None, 'spatial': 'uniform'},
    'Nap_Et2': {'gNap_Et2bar': None, 'spatial': 'uniform'},
    'SK_E2': {'gSK_E2bar': None, 'spatial': 'uniform'},
    'SKv3_1': {'gSKv3_1bar': None, 'spatial': 'uniform'},
    'pas': {'e': -90, 'g': None, 'spatial': 'uniform'}}},
  'properties': {'Ra': 100.0, 'cm': 1.0, 'ions': {'ek': -85.0, 'ena': 50.0}}},
 'ApicalDendrite': {'mechanisms': {'global': {},
   'range': {'CaDynamics_E2_v2': {'decay': None,
     'gamma': None,
     'spatial': 'uniform'},
    'Ca_HVA': {'begin': None,
     'end': None,
     'gCa_HVAbar': None,
     'outsidescale': 0.1,
     'spatial': 'uniform_range'},
    'Ca_LVAst': {'begin': None,
     'end': None,
     'gCa_LVAstbar': None,
     'outsidescale': 0.01,
     'spatial': 'uniform_range'},
    'Ih': {'_lambda': 3.6161,
     'distance': 'relative',
     'gIhbar': 0.0002,
     'linScale': None,
     'offset': -0.8696,
     'max_g': None,
     'spatial': 'capped_exponential',
     'xOffset': 0.0},
    'Im': {'gImbar': None, 'spatial': 'uniform'},
    'NaTa_t': {'gNaTa_tbar': None, 'spatial': 'uniform'},
    'SK_E2': {'gSK_E2bar': None, 'spatial': 'uniform'},
    'SKv3_1': {'distance': 'relative',
     'gSKv3_1bar': None,
     'offset': None,
     'slope': None,
     'spatial': 'linear'},
    'pas': {'e': -90, 'g': None, 'spatial': 'uniform'}}},
  'properties': {'Ra': 100.0, 'cm': 2.0, 'ions': {'ek': -85.0, 'ena': 50.0}}},
 'Dendrite': {'mechanisms': {'global': {},
   'range': {'Ih': {'gIhbar': 0.0002, 'spatial': 'uniform'},
    'pas': {'e': -90.0, 'g': None, 'spatial': 'uniform'}}},
  'properties': {'Ra': 100.0, 'cm': 2.0}},
 'Myelin': {'mechanisms': {'global': {},
   'range': {'pas': {'e': -90.0, 'g': 4e-05, 'spatial': 'uniform'}}},
  'properties': {'Ra': 100.0, 'cm': 0.02}},
 'Soma': {'mechanisms': {'global': {},
   'range': {'CaDynamics_E2_v2': {'decay': None,
     'gamma': None,
     'spatial': 'uniform'},
    'Ca_HVA': {'gCa_HVAbar': None, 'spatial': 'uniform'},
    'Ca_LVAst': {'gCa_LVAstbar': None, 'spatial': 'uniform'},
    'Ih': {'gIhbar': 8e-05, 'spatial': 'uniform'},
    'K_Pst': {'gK_Pstbar': None, 'spatial': 'uniform'},
    'K_Tst': {'gK_Tstbar': None, 'spatial': 'uniform'},
    'NaTa_t': {'gNaTa_tbar': None, 'spatial': 'uniform'},
    'Nap_Et2': {'gNap_Et2bar': None, 'spatial': 'uniform'},
    'SK_E2': {'gSK_E2bar': None, 'spatial': 'uniform'},
    'SKv3_1': {'gSKv3_1bar': None, 'spatial': 'uniform'},
    'pas': {'e': -90, 'g': None, 'spatial': 'uniform'}}},
  'properties': {'Ra': 100.0, 'cm': 1.0, 'ions': {'ek': -85.0, 'ena': 50.0}}},
 'cell_modify_functions': {'scale_apical': {'scale': None, 'compartment': compartment}},
 'filename': None,
 'discretization': {'max_seg_length': 50, 'f': 100}}
    parameter_template = scp.NTParameterSet(parameter_template)
    return parameter_template    
params_v3 = {'min': {'ephys.CaDynamics_E2_v2.apic.decay': 20.0, 'ephys.CaDynamics_E2_v2.apic.gamma': 0.0005, 'ephys.CaDynamics_E2_v2.axon.decay': 20.0, 'ephys.CaDynamics_E2_v2.axon.gamma': 0.0005, 'ephys.CaDynamics_E2_v2.soma.decay': 20.0, 'ephys.CaDynamics_E2_v2.soma.gamma': 0.0005, 'ephys.Ca_HVA.apic.gCa_HVAbar': 0.0, 'ephys.Ca_HVA.axon.gCa_HVAbar': 0.0, 'ephys.Ca_HVA.soma.gCa_HVAbar': 0.0, 'ephys.Ca_LVAst.apic.gCa_LVAstbar': 0.0, 'ephys.Ca_LVAst.axon.gCa_LVAstbar': 0.0, 'ephys.Ca_LVAst.soma.gCa_LVAstbar': 0.0, 'ephys.Ih.apic.linScale': 1.5, 'ephys.Ih.apic.max_g': 0.003, 'ephys.Im.apic.gImbar': 0.0, 'ephys.K_Pst.axon.gK_Pstbar': 0.0, 'ephys.K_Pst.soma.gK_Pstbar': 0.0, 'ephys.K_Tst.axon.gK_Tstbar': 0.0, 'ephys.K_Tst.soma.gK_Tstbar': 0.0, 'ephys.NaTa_t.apic.gNaTa_tbar': 0.0, 'ephys.NaTa_t.axon.gNaTa_tbar': 0.0, 'ephys.NaTa_t.soma.gNaTa_tbar': 0.0, 'ephys.Nap_Et2.axon.gNap_Et2bar': 0.0, 'ephys.Nap_Et2.soma.gNap_Et2bar': 0.0, 'ephys.SK_E2.apic.gSK_E2bar': 0.0, 'ephys.SK_E2.axon.gSK_E2bar': 0.0, 'ephys.SK_E2.soma.gSK_E2bar': 0.0, 'ephys.SKv3_1.apic.gSKv3_1bar': 0.0, 'ephys.SKv3_1.apic.offset': 0.0, 'ephys.SKv3_1.apic.slope': -3.0, 'ephys.SKv3_1.axon.gSKv3_1bar': 0.0, 'ephys.SKv3_1.soma.gSKv3_1bar': 0.0, 'ephys.none.apic.g_pas': 3e-05, 'ephys.none.axon.g_pas': 2e-05, 'ephys.none.dend.g_pas': 3e-05, 'ephys.none.soma.g_pas': 2e-05, 'scale_apical.scale': 0.5}, 'max': {'ephys.CaDynamics_E2_v2.apic.decay': 200.0, 'ephys.CaDynamics_E2_v2.apic.gamma': 0.05, 'ephys.CaDynamics_E2_v2.axon.decay': 1000.0, 'ephys.CaDynamics_E2_v2.axon.gamma': 0.05, 'ephys.CaDynamics_E2_v2.soma.decay': 1000.0, 'ephys.CaDynamics_E2_v2.soma.gamma': 0.05, 'ephys.Ca_HVA.apic.gCa_HVAbar': 0.005, 'ephys.Ca_HVA.axon.gCa_HVAbar': 0.001, 'ephys.Ca_HVA.soma.gCa_HVAbar': 0.001, 'ephys.Ca_LVAst.apic.gCa_LVAstbar': 0.2, 'ephys.Ca_LVAst.axon.gCa_LVAstbar': 0.01, 'ephys.Ca_LVAst.soma.gCa_LVAstbar': 0.01, 'ephys.Ih.apic.linScale': 10.0, 'ephys.Ih.apic.max_g': 0.015, 'ephys.Im.apic.gImbar': 0.001, 'ephys.K_Pst.axon.gK_Pstbar': 1.0, 'ephys.K_Pst.soma.gK_Pstbar': 1.0, 'ephys.K_Tst.axon.gK_Tstbar': 0.1, 'ephys.K_Tst.soma.gK_Tstbar': 0.1, 'ephys.NaTa_t.apic.gNaTa_tbar': 0.04, 'ephys.NaTa_t.axon.gNaTa_tbar': 4.0, 'ephys.NaTa_t.soma.gNaTa_tbar': 4.0, 'ephys.Nap_Et2.axon.gNap_Et2bar': 0.01, 'ephys.Nap_Et2.soma.gNap_Et2bar': 0.01, 'ephys.SK_E2.apic.gSK_E2bar': 0.01, 'ephys.SK_E2.axon.gSK_E2bar': 0.1, 'ephys.SK_E2.soma.gSK_E2bar': 0.1, 'ephys.SKv3_1.apic.gSKv3_1bar': 0.04, 'ephys.SKv3_1.apic.offset': 1.0, 'ephys.SKv3_1.apic.slope': 0.0, 'ephys.SKv3_1.axon.gSKv3_1bar': 2.0, 'ephys.SKv3_1.soma.gSKv3_1bar': 2.0, 'ephys.none.apic.g_pas': 0.0001, 'ephys.none.axon.g_pas': 5e-05, 'ephys.none.dend.g_pas': 0.0001, 'ephys.none.soma.g_pas': 5.02e-05, 'scale_apical.scale': 3.0}}

def get_template_v4(compartment = None):
    parameter_template = {'AIS': {'mechanisms': {'global': {},
   'range': {'CaDynamics_E2_v2': {'decay': None,
     'gamma': None,
     'spatial': 'uniform'},
    'Ca_HVA': {'gCa_HVAbar': None, 'spatial': 'uniform'},
    'Ca_LVAst': {'gCa_LVAstbar': None, 'spatial': 'uniform'},
    'Ih': {'gIhbar': 8e-05, 'spatial': 'uniform'},
    'K_Pst': {'gK_Pstbar': None, 'spatial': 'uniform'},
    'K_Tst': {'gK_Tstbar': None, 'spatial': 'uniform'},
    'NaTa_t': {'gNaTa_tbar': None, 'spatial': 'uniform'},
    'Nap_Et2': {'gNap_Et2bar': None, 'spatial': 'uniform'},
    'SK_E2': {'gSK_E2bar': None, 'spatial': 'uniform'},
    'SKv3_1': {'gSKv3_1bar': None, 'spatial': 'uniform'},
    'pas': {'e': -90, 'g': None, 'spatial': 'uniform'}}},
  'properties': {'Ra': 100.0, 'cm': 1.0, 'ions': {'ek': -85.0, 'ena': 50.0}}},
 'ApicalDendrite': {'mechanisms': {'global': {},
   'range': {'CaDynamics_E2_v2': {'decay': None,
     'gamma': None,
     'spatial': 'uniform'},
    'Ca_HVA': {'begin': None,
     'end': None,
     'gCa_HVAbar': None,
     'outsidescale': 0.1,
     'spatial': 'uniform_range'},
    'Ca_LVAst': {'begin': None,
     'end': None,
     'gCa_LVAstbar': None,
     'outsidescale': 0.01,
     'spatial': 'uniform_range'},
    'Ih': {'_lambda': 3.6161,
     'distance': 'relative',
     'gIhbar': 0.0002,
     'linScale': None,
     'offset': -0.8696,
     'max_g': None,
     'spatial': 'capped_exponential',
     'xOffset': 0.0},
    'Im': {'gImbar': None, 'spatial': 'uniform'},
    'NaTa_t': {'spatial': 'linear_capped',
               'prox_value': None,
               'dist_value': None,
               'dist_value_distance': None,
               'distance': 'relative',
               'param_name': 'gNaTa_tbar'},
    'SK_E2': {'gSK_E2bar': None, 'spatial': 'uniform'},
    'SKv3_1': {'distance': 'relative',
     'gSKv3_1bar': None,
     'offset': None,
     'slope': None,
     'spatial': 'linear'},
    'pas': {'e': -90, 'g': None, 'spatial': 'uniform'}}},
  'properties': {'Ra': 100.0, 'cm': 2.0, 'ions': {'ek': -85.0, 'ena': 50.0}}},
 'Dendrite': {'mechanisms': {'global': {},
   'range': {'Ih': {'gIhbar': 0.0002, 'spatial': 'uniform'},
    'pas': {'e': -90.0, 'g': None, 'spatial': 'uniform'}}},
  'properties': {'Ra': 100.0, 'cm': 2.0}},
 'Myelin': {'mechanisms': {'global': {},
   'range': {'pas': {'e': -90.0, 'g': 4e-05, 'spatial': 'uniform'}}},
  'properties': {'Ra': 100.0, 'cm': 0.02}},
 'Soma': {'mechanisms': {'global': {},
   'range': {'CaDynamics_E2_v2': {'decay': None,
     'gamma': None,
     'spatial': 'uniform'},
    'Ca_HVA': {'gCa_HVAbar': None, 'spatial': 'uniform'},
    'Ca_LVAst': {'gCa_LVAstbar': None, 'spatial': 'uniform'},
    'Ih': {'gIhbar': 8e-05, 'spatial': 'uniform'},
    'K_Pst': {'gK_Pstbar': None, 'spatial': 'uniform'},
    'K_Tst': {'gK_Tstbar': None, 'spatial': 'uniform'},
    'NaTa_t': {'gNaTa_tbar': None, 'spatial': 'uniform'},
    'Nap_Et2': {'gNap_Et2bar': None, 'spatial': 'uniform'},
    'SK_E2': {'gSK_E2bar': None, 'spatial': 'uniform'},
    'SKv3_1': {'gSKv3_1bar': None, 'spatial': 'uniform'},
    'pas': {'e': -90, 'g': None, 'spatial': 'uniform'}}},
  'properties': {'Ra': 100.0, 'cm': 1.0, 'ions': {'ek': -85.0, 'ena': 50.0}}},
 'cell_modify_functions': {'scale_apical': {'scale': None, 'compartment': compartment}},
 'filename': None,
 'discretization': {'max_seg_length': 50, 'f': 100}}
    parameter_template = scp.NTParameterSet(parameter_template)
    return parameter_template

params_v4 = {'min': {'ephys.CaDynamics_E2_v2.apic.decay': 20.0, 'ephys.CaDynamics_E2_v2.apic.gamma': 0.0005, 'ephys.CaDynamics_E2_v2.axon.decay': 20.0, 'ephys.CaDynamics_E2_v2.axon.gamma': 0.0005, 'ephys.CaDynamics_E2_v2.soma.decay': 20.0, 'ephys.CaDynamics_E2_v2.soma.gamma': 0.0005, 'ephys.Ca_HVA.apic.gCa_HVAbar': 0.0, 'ephys.Ca_HVA.axon.gCa_HVAbar': 0.0, 'ephys.Ca_HVA.soma.gCa_HVAbar': 0.0, 'ephys.Ca_LVAst.apic.gCa_LVAstbar': 0.0, 'ephys.Ca_LVAst.axon.gCa_LVAstbar': 0.0, 'ephys.Ca_LVAst.soma.gCa_LVAstbar': 0.0, 'ephys.Ih.apic.linScale': 1.5, 'ephys.Ih.apic.max_g': 0.003, 'ephys.Im.apic.gImbar': 0.0, 'ephys.K_Pst.axon.gK_Pstbar': 0.0, 'ephys.K_Pst.soma.gK_Pstbar': 0.0, 'ephys.K_Tst.axon.gK_Tstbar': 0.0, 'ephys.K_Tst.soma.gK_Tstbar': 0.0, 'ephys.NaTa_t.axon.gNaTa_tbar': 0.0, 'ephys.NaTa_t.soma.gNaTa_tbar': 0.0, 'ephys.Nap_Et2.axon.gNap_Et2bar': 0.0, 'ephys.Nap_Et2.soma.gNap_Et2bar': 0.0, 'ephys.SK_E2.apic.gSK_E2bar': 0.0, 'ephys.SK_E2.axon.gSK_E2bar': 0.0, 'ephys.SK_E2.soma.gSK_E2bar': 0.0, 'ephys.SKv3_1.apic.gSKv3_1bar': 0.0, 'ephys.SKv3_1.apic.offset': 0.0, 'ephys.SKv3_1.apic.slope': -3.0, 'ephys.SKv3_1.axon.gSKv3_1bar': 0.0, 'ephys.SKv3_1.soma.gSKv3_1bar': 0.0, 'ephys.none.apic.g_pas': 3e-05, 'ephys.none.axon.g_pas': 2e-05, 'ephys.none.dend.g_pas': 3e-05, 'ephys.none.soma.g_pas': 2e-05, 'scale_apical.scale': 0.5, 'ephys.NaTa_t.apic.prox_value': 0.0, 'ephys.NaTa_t.apic.dist_value': 0.0, 'ephys.NaTa_t.apic.dist_value_distance': 0.0}, 'max': {'ephys.CaDynamics_E2_v2.apic.decay': 200.0, 'ephys.CaDynamics_E2_v2.apic.gamma': 0.05, 'ephys.CaDynamics_E2_v2.axon.decay': 1000.0, 'ephys.CaDynamics_E2_v2.axon.gamma': 0.05, 'ephys.CaDynamics_E2_v2.soma.decay': 1000.0, 'ephys.CaDynamics_E2_v2.soma.gamma': 0.05, 'ephys.Ca_HVA.apic.gCa_HVAbar': 0.005, 'ephys.Ca_HVA.axon.gCa_HVAbar': 0.001, 'ephys.Ca_HVA.soma.gCa_HVAbar': 0.001, 'ephys.Ca_LVAst.apic.gCa_LVAstbar': 0.2, 'ephys.Ca_LVAst.axon.gCa_LVAstbar': 0.01, 'ephys.Ca_LVAst.soma.gCa_LVAstbar': 0.01, 'ephys.Ih.apic.linScale': 10.0, 'ephys.Ih.apic.max_g': 0.015, 'ephys.Im.apic.gImbar': 0.001, 'ephys.K_Pst.axon.gK_Pstbar': 1.0, 'ephys.K_Pst.soma.gK_Pstbar': 1.0, 'ephys.K_Tst.axon.gK_Tstbar': 0.1, 'ephys.K_Tst.soma.gK_Tstbar': 0.1, 'ephys.NaTa_t.axon.gNaTa_tbar': 4.0, 'ephys.NaTa_t.soma.gNaTa_tbar': 4.0, 'ephys.Nap_Et2.axon.gNap_Et2bar': 0.01, 'ephys.Nap_Et2.soma.gNap_Et2bar': 0.01, 'ephys.SK_E2.apic.gSK_E2bar': 0.01, 'ephys.SK_E2.axon.gSK_E2bar': 0.1, 'ephys.SK_E2.soma.gSK_E2bar': 0.1, 'ephys.SKv3_1.apic.gSKv3_1bar': 0.04, 'ephys.SKv3_1.apic.offset': 1.0, 'ephys.SKv3_1.apic.slope': 0.0, 'ephys.SKv3_1.axon.gSKv3_1bar': 2.0, 'ephys.SKv3_1.soma.gSKv3_1bar': 2.0, 'ephys.none.apic.g_pas': 0.0001, 'ephys.none.axon.g_pas': 5e-05, 'ephys.none.dend.g_pas': 0.0001, 'ephys.none.soma.g_pas': 5.02e-05, 'scale_apical.scale': 3.0, 'ephys.NaTa_t.apic.prox_value': 0.04, 'ephys.NaTa_t.apic.dist_value': 0.04, 'ephys.NaTa_t.apic.dist_value_distance': 1.0}}

params_v3 = I.pd.DataFrame(params_v3)
params_v4 = I.pd.DataFrame(params_v4)