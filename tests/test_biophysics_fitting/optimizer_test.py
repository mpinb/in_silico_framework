import Interface as I
from . import decorators
import unittest
# import global variables from context
from .context import PARENT, DATA_DIR
# import context
import distributed

from biophysics_fitting import hay_complete_default_setup, L5tt_parameter_setup
from biophysics_fitting.parameters import param_to_kwargs
from biophysics_fitting.optimizer import start_run


# class FakeFuture():
#     def __init__(self, f):
#         self.f = f
#     def result(self):
#         return self.f
#     
# class FakeClient():
#     def compute(self, *args, **kwargs):
#         res = I.dask.compute(*args, get = I.dask.get)
#         return [FakeFuture(r) for r in res]

from biophysics_fitting.hay_evaluation import setup_hay_evaluator

def set_up_mdb(step = False):
    '''completely sets up a model data base in a temporary folder for opimization'''
    def get_template():
        param = L5tt_parameter_setup.get_L5tt_template()
        param.ApicalDendrite.mechanisms.range.SKv3_1 = I.scp.NTParameterSet({
                'slope': None,
                'distance': 'relative',
                'gSKv3_1bar': None,
                'offset': None,
                'spatial': 'linear'})
        param['cell_modify_functions'] = I.scp.NTParameterSet({'scale_apical': {'scale': None}})
        return param

    def scale_apical(cell_param, params):
        assert(len(params) == 1)
        cell_param.cell_modify_functions.scale_apical.scale = params['scale']
        return cell_param    
            
    params = hay_complete_default_setup.get_feasible_model_params().drop('x', axis = 1)
    params.index = 'ephys.' + params.index
    params = params.append(I.pd.DataFrame({'ephys.SKv3_1.apic.slope': {'min': -3, 'max': 0},
                                           'ephys.SKv3_1.apic.offset': {'min': 0, 'max': 1}}).T)
    params = params.append(I.pd.DataFrame({'min': .333, 'max': 3}, index = ['scale_apical.scale']))
    params = params.sort_index()
    
    def get_Simulator(mdb_setup, step = step):
        fixed_params = mdb_setup['get_fixed_params'](mdb_setup)
        s = hay_complete_default_setup.get_Simulator(I.pd.Series(fixed_params), step = step)
        s.setup.cell_param_generator = get_template
        s.setup.cell_param_modify_funs.append(('scale_apical', scale_apical))
        #s.setup.cell_modify_funs.append(('scale_apical', param_to_kwargs(scale_apical)))    
        return s
        
    def get_Evaluator(mdb_setup, step = step):
        return hay_complete_default_setup.get_Evaluator(step = step)
        
    def get_Combiner(mdb_setup, step = step):
        return hay_complete_default_setup.get_Combiner(step = step)
    
    tempdir = I.tempfile.mkdtemp()
    mdb = I.ModelDataBase(tempdir)    
    mdb.create_sub_mdb('86')
    
    mdb['86'].create_managed_folder('morphology')
    I.shutil.copy(I.os.path.join(DATA_DIR, '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2.hoc'),
        mdb['86']['morphology'].join('86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2.hoc')) #

    mdb['86']['fixed_params'] = {'BAC.hay_measure.recSite': 835,
        'BAC.stim.dist': 835,
        'bAP.hay_measure.recSite1':835,
        'bAP.hay_measure.recSite2':1015,
        'hot_zone.min_': 900,
        'hot_zone.max_': 1100,
        'morphology.filename': None}
    
    def get_fixed_params(mdb_setup):
        fixed_params = mdb_setup['fixed_params']
        fixed_params['morphology.filename'] = mdb_setup['morphology'].get_file('hoc')
        return fixed_params    
    
    mdb['86']['get_fixed_params'] = get_fixed_params    
    mdb['86'].setitem('params', params, dumper = I.dumper_pandas_to_pickle)    
    mdb['86'].setitem('get_Simulator', I.partial(get_Simulator, step = True), dumper = I.dumper_to_cloudpickle)
    mdb['86'].setitem('get_Evaluator', I.partial(get_Evaluator, step = True), dumper = I.dumper_to_cloudpickle)
    mdb['86'].setitem('get_Combiner', I.partial(get_Combiner, step = True), dumper = I.dumper_to_cloudpickle)   
    
    return mdb 

def get_params():
    params = {'ephys.CaDynamics_E2.apic.decay': 21.562782924214414,
         'ephys.CaDynamics_E2.apic.gamma': 0.00050335450968099567,
         'ephys.CaDynamics_E2.axon.decay': 634.68027789684118,
         'ephys.CaDynamics_E2.axon.gamma': 0.018260790347751195,
         'ephys.CaDynamics_E2.soma.decay': 414.24643364256787,
         'ephys.CaDynamics_E2.soma.gamma': 0.037100474329548119,
         'ephys.Ca_HVA.apic.gCa_HVAbar': 0.0045175821836125098,
         'ephys.Ca_HVA.axon.gCa_HVAbar': 0.00097268930234091803,
         'ephys.Ca_HVA.soma.gCa_HVAbar': 6.0448867992547778e-06,
         'ephys.Ca_LVAst.apic.gCa_LVAstbar': 0.057965973436719803,
         'ephys.Ca_LVAst.axon.gCa_LVAstbar': 0.0050778726879885704,
         'ephys.Ca_LVAst.soma.gCa_LVAstbar': 0.00022413105836493485,
         'ephys.Im.apic.gImbar': 0.00014023587655362564,
         'ephys.K_Pst.axon.gK_Pstbar': 0.4925941891152068,
         'ephys.K_Pst.soma.gK_Pstbar': 0.16068221697454338,
         'ephys.K_Tst.axon.gK_Tstbar': 0.014678352199646584,
         'ephys.K_Tst.soma.gK_Tstbar': 0.084088090845191005,
         'ephys.NaTa_t.apic.gNaTa_tbar': 0.019772619077393836,
         'ephys.NaTa_t.axon.gNaTa_tbar': 0.06042182368673929,
         'ephys.NaTa_t.soma.gNaTa_tbar': 3.5579330132905831,
         'ephys.Nap_Et2.axon.gNap_Et2bar': 0.0075521417579080402,
         'ephys.Nap_Et2.soma.gNap_Et2bar': 0.0017051223333636512,
         'ephys.SK_E2.apic.gSK_E2bar': 0.0048389916157663415,
         'ephys.SK_E2.axon.gSK_E2bar': 0.00026717820773407248,
         'ephys.SK_E2.soma.gSK_E2bar': 0.062625778876627305,
         'ephys.SKv3_1.apic.gSKv3_1bar': 0.007722918904069901,
         'ephys.SKv3_1.apic.offset': 0.19821935071220703,
         'ephys.SKv3_1.apic.slope': -0.02188881181300692,
         'ephys.SKv3_1.axon.gSKv3_1bar': 1.3368072275107978,
         'ephys.SKv3_1.soma.gSKv3_1bar': 0.7506944445180439,
         'ephys.none.apic.g_pas': 3.1841791686836539e-05,
         'ephys.none.axon.g_pas': 4.7550177118866432e-05,
         'ephys.none.dend.g_pas': 6.3767970209653598e-05,
         'ephys.none.soma.g_pas': 3.7758776052976391e-05,
         'scale_apical.scale': 2.9468848475576652}
    return I.pd.Series(params)
 
def get_features():
    features = {'AI1': 1.44214547254434,
 'AI2': 1.8621624399987309,
 'AI3': 1.2227697700239537,
 'APh1': 0.4824890286180915,
 'APh2': 1.1730880305600762,
 'APh3': 0.8630230788958962,
 'APw1': 2.1209738238787468,
 'APw2': 1.49493668495702,
 'APw3': 2.202446173847188,
 'BAC_APheight': 1.189288126417369,
 'BAC_ISI': 1.6533467527070829,
 'BAC_ahpdepth': 0.173977452758308,
 'BAC_caSpike_height': 0.6505765966883501,
 'BAC_caSpike_width': 0.6273765002883814,
 'BAC_spikecount': 0.0,
 'DI1': 0.2757174736052093,
 'DI2': 1.945974735191181,
 'ISIcv1': 0.1405598748172335,
 'ISIcv2': 0.6196284887118612,
 'ISIcv3': 0.623823468288825,
 'TTFS1': 1.3941506092050748,
 'TTFS2': 0.11238803257276951,
 'TTFS3': 0.4061175048187806,
 'bAP_APheight': 2.6130920420935255,
 'bAP_APwidth': 1.977107145357195,
 'bAP_att2': 2.814176978326466,
 'bAP_att3': 3.012709359315379,
 'bAP_spikecount': 0.0,
 'fAHPd1': 1.6724044404002458,
 'fAHPd2': 1.3099824082131681,
 'fAHPd3': 1.1288951143041914,
 'mf1': 0.5681818181818182,
 'mf2': 0.8928571428571428,
 'mf3': 0.4500045000450005,
 'sAHPd1': 0.846713167980323,
 'sAHPd2': 0.19818032040716757,
 'sAHPd3': 0.08981352935128958,
 'sAHPt1': 1.8570329292981904,
 'sAHPt2': 1.8350114629840846,
 'sAHPt3': 2.312944420748147}
    return features

# def get_features():
#     features = {'AI1': 1.4514855341790294,
#      'AI2': 1.866209637356929,
#      'AI3': 1.2535217463256214,
#      'APh1': 0.48186876223965763,
#      'APh2': 1.172156056431221,
#      'APh3': 0.863650042528163,
#      'APw1': 2.057406879413192,
#      'APw2': 1.4943625405612135,
#      'APw3': 2.1943465498434445,
#      'BAC_APheight': 1.1867727153194332,
#      'BAC_ISI': 1.6486416973045854,
#      'BAC_ahpdepth': 0.17734715653576494,
#      'BAC_caSpike_height': 0.6655060068690136,
#      'BAC_caSpike_width': 0.7185938141435386,
#      'BAC_spikecount': 0.0,
#      'DI1': 0.2694597586494436,
#      'DI2': 1.9461882029782838,
#      'ISIcv1': 0.15594372606388032,
#      'ISIcv2': 0.6213835363369604,
#      'ISIcv3': 0.628778439027531,
#      'TTFS1': 1.3825925026279664,
#      'TTFS2': 0.11583649368413243,
#      'TTFS3': 0.39617963459284056,
#      'bAP_APheight': 2.6143538343280768,
#      'bAP_APwidth': 1.933572595558644,
#      'bAP_att2': 2.814542100265043,
#      'bAP_att3': 3.0141049263005457,
#      'bAP_spikecount': 0.0,
#      'fAHPd1': 1.671995191441434,
#      'fAHPd2': 1.309566990267767,
#      'fAHPd3': 1.1296345340770357,
#      'mf1': 0.5681818181818182,
#      'mf2': 0.8928571428571428,
#      'mf3': 0.4500045000450005,
#      'sAHPd1': 0.8467747434406173,
#      'sAHPd2': 0.19777077739995486,
#      'sAHPd3': 0.08901170201281382,
#      'sAHPt1': 1.8668195330751702,
#      'sAHPt2': 1.8463328922218634,
#      'sAHPt3': 2.2630559405104367}
#     return features


class Tests(unittest.TestCase):       
    def setUp(self):
        pass

    @decorators.testlevel(2)    
    def test_mini_optimization_run(self):
        c = distributed.client_object_duck_typed
        try:
            mdb = set_up_mdb(step = False)
            start_run(mdb['86'], 1, client = c, offspring_size = 2, max_ngen = 2)
            # accessing simulation results of run
            keys = [int(k) for k in list(mdb['86']['1'].keys()) if I.utils.convertible_to_int(k)]
            assert(max(keys) == 2)
            # if continue_cp is not set (defaults to False), an Exception is raised if the same 
            # optimization is started again
            self.assertRaises(ValueError, lambda: start_run(mdb['86'], 1, client = c, offspring_size = 2, max_ngen = 4))
            # with continue_cp = True, the optimization gets continued
            start_run(mdb['86'], 1, client = c, offspring_size = 2, max_ngen = 4, continue_cp = True)
            keys = [int(k) for k in list(mdb['86']['1'].keys()) if I.utils.convertible_to_int(k)]
            assert(max(keys) == 4)
            start_run(mdb['86'], 2, client = c, offspring_size = 2, max_ngen = 2)
            keys = [int(k) for k in list(mdb['86']['2'].keys()) if I.utils.convertible_to_int(k)]
            assert(max(keys) == 2)   
        except:
            I.shutil.rmtree(mdb.basedir)     
            raise
    
    @decorators.testlevel(3)    
    def test_ON_HOLD_legacy_simulator_and_new_simulator_give_same_results(self):
        setup_hay_evaluator() # this adds a stump cell to the neuron environment,which is
        # necessary to acces the hay evaluate functions. For the vairalbe time step solver,
        # this changes the step size and can therefore minimally change the results.
        # before testing reproducability, it is therefore necessary to initialize
        # the evaluator

        mdb_legacy = I.ModelDataBase(I.os.path.join(DATA_DIR, 
                                                    'example_Kv3_1_slope_variable_dend_scale_step'),
                                     readonly = True)#
                                      
        mdb_new = set_up_mdb(step = True)
        try:
            s_legacy = mdb_legacy['86']['get_Simulator'](mdb_legacy['86'])
            s_new = mdb_new['86']['get_Simulator'](mdb_new['86'])
            e_legacy = mdb_legacy['86']['get_Evaluator'](mdb_legacy['86'])
            e_new = mdb_new['86']['get_Evaluator'](mdb_new['86'])
            with I.silence_stdout:
                # initialize 
                features_legacy = e_legacy.evaluate(s_legacy.run(get_params()))
                # 'correct' run
                features_legacy = e_legacy.evaluate(s_legacy.run(get_params()))
                features_new = e_new.evaluate(s_new.run(get_params()))
                 
        except:
            I.shutil.rmtree(mdb_new.basedir)     
            raise
         
        for k in list(features_legacy.keys()):
            assert(features_legacy[k] == features_new[k])
            
    def test_reproducability(self):
        
        setup_hay_evaluator() # this adds a stump cell to the neuron environment,which is
        # necessary to acces the hay evaluate functions. For the vairalbe time step solver,
        # this changes the step size and can therefore minimally change the results.
        # before testing reproducability, it is therefore necessary to initialize
        # the evaluator
        mdb_new = set_up_mdb(step = True)
        try:
            s_new = mdb_new['86']['get_Simulator'](mdb_new['86'], step = False)
            e_new = mdb_new['86']['get_Evaluator'](mdb_new['86'], step = False)
            with I.silence_stdout:
                features_new = e_new.evaluate(s_new.run(get_params()))
        except:
            I.shutil.rmtree(mdb_new.basedir)     
            raise
        
        features_legacy = get_features()
        for k in list(features_new.keys()):
#             assert(features_legacy[k] == features_new[k]) rieke - values are not exactly the same
            I.np.testing.assert_almost_equal(features_new[k], features_legacy[k], decimal = 6)
              