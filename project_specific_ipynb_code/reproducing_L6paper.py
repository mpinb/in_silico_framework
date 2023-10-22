'''THis module contains code to facilitate computations in the ipynb files that 
contain the name '_reproducing_L6paper_ in /nas1/Data_arco/notebooks'''

import Interface as I
from simrun2.reduced_model.get_kernel import compare_lists_by_none_values
from single_cell_parser.network_param_modify_functions import set_stim_onset
from single_cell_parser.network_param_modify_functions import change_ongoing_interval
from single_cell_parser import network
import biophysics_fitting.utils
from biophysics_fitting.hay_evaluation import objectives_BAC, objectives_step
import simrun3.utils
import simrun3.synaptic_strength_fitting
import six

###########################
# setting up model data base
###########################


class L6config:

    def __init__(
            self,
            mdb=None,
            biophysical_model_mdb=None,
            biophysical_model_mdb_key=None,
            anatomical_model_mdb=None,
            anatomical_model_mdb_key=None,
            hocpath=None,
            runs=None,
            locs=[
                'C2center', 'C1border', 'C3border', 'B1border', 'B2border',
                'B3border', 'D1border', 'D2border', 'D3border'
            ],
            stims=['B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'D1', 'D2', 'D3', 'E2']):
        assert mdb is not None
        assert biophysical_model_mdb is not None
        assert biophysical_model_mdb_key is not None
        assert anatomical_model_mdb is not None
        assert runs is not None
        assert hocpath is not None
        self.mdb = mdb
        self.biophysical_model_mdb = biophysical_model_mdb
        self.biophysical_model_mdb_key = biophysical_model_mdb_key
        self.anatomical_model_mdb = anatomical_model_mdb
        if anatomical_model_mdb_key is not None:
            self.anatomical_model_mdb_key = anatomical_model_mdb_key
        else:
            self.anatomical_model_mdb_key = biophysical_model_mdb_key
        self.runs = runs
        self.hocpath = hocpath
        self.locs = locs
        self.stims = stims

    def setup_mdb(self):
        '''copies all files at the appropriate location in this mdb'''
        mdb = self.mdb
        if not 'morphology' in list(mdb.keys()):
            print('copying morphology {}'.format(self.hocpath))
            mdb.create_managed_folder('morphology')
            I.shutil.copy(self.hocpath, mdb['morphology'])

        # copying this, because we might have a different morpholgy here compared to the
        # biophysics fitting, which might be incompatzible with the confile.
        for k in [
                'fixed_params', 'get_Combiner', 'get_Evaluator',
                'get_Simulator', 'get_fixed_params', 'params'
        ]:
            mdb[k] = self.biophysical_model_mdb[
                self.biophysical_model_mdb_key][k]

        if not 'network_embedding' in list(mdb.keys()):
            print('create network embedding subfolder')
            mdb.create_sub_mdb('network_embedding')
        for loc in self.locs:
            if not loc in list(mdb['network_embedding'].keys()):
                print('creating network_embedding subfolder for {}'.format(loc))
                mdb['network_embedding'].create_managed_folder(loc)

        def get_file_or_folder_that_startswith(path, startswith):
            paths = [p for p in I.os.listdir(path) if p.startswith(startswith)]
            assert len(paths) == 1
            return I.os.path.join(path, paths[0])

        def get_file_or_folder_that_endswith(path, endswith):
            paths = [p for p in I.os.listdir(path) if p.endswith(endswith)]
            assert len(paths) == 1
            return I.os.path.join(path, paths[0])

        print('')
        print('creating number of cells spreadsheet from confile')
        from singlecell_input_mapper.singlecell_input_mapper import con_file_to_NumberOfConnectedCells_sheet
        for loc in self.locs:
            d = self.anatomical_model_mdb[self.anatomical_model_mdb_key]
            p = get_file_or_folder_that_startswith(d, loc + '_')
            syn = get_file_or_folder_that_endswith(p, '.syn')
            con = get_file_or_folder_that_endswith(p, '.con')
            I.shutil.copy(syn, mdb['network_embedding'][loc].join('con.syn'))
            I.shutil.copy(con, mdb['network_embedding'][loc].join('con.con'))
            con_file_to_NumberOfConnectedCells_sheet(
                mdb['network_embedding'][loc].join('con.con'))
            print(con)

        print('')
        print('create evoked activity parameterfiles')
        from getting_started import getting_started_dir
        ongoing_template_param_name = I.os.path.join(
            getting_started_dir,
            'functional_constraints/ongoing_activity/ongoing_activity_celltype_template_exc_conductances_fitted.param'
        )
        print('template: {}'.format(ongoing_template_param_name))

        for loc in self.locs:
            for stim in self.stims:
                print('\tstim: {}, loc: {}'.format(stim, loc))
                ongoing_template_param_name = I.os.path.join(
                    getting_started_dir,
                    'functional_constraints/ongoing_activity/ongoing_activity_celltype_template_exc_conductances_fitted.param'
                )
                cell_number_file_name = mdb['network_embedding'][loc].join(
                    'NumberOfConnectedCells.csv')
                syn_file_path = mdb['network_embedding'][loc].join('con.syn')
                con_file_path = mdb['network_embedding'][loc].join('con.con')
                cell_number_file_name = mdb['network_embedding'][loc].join(
                    'NumberOfConnectedCells.csv')
                with I.silence_stdout:
                    I.create_evoked_network_parameter(
                        ongoing_template_param_name, cell_number_file_name,
                        syn_file_path, con_file_path, stim,
                        mdb['network_embedding'][loc].join(stim +
                                                           '_network.param'))

        print()

    def get_network_param(self,
                          loc='C2center',
                          stim='C2',
                          network_param_modfuns=[],
                          stim_onset=2000):
        network_param = self.mdb['network_embedding'][loc].join(
            '{}_network.param'.format(stim))
        network_param = I.scp.build_parameters(network_param)
        for fun in network_param_modfuns:
            fun(network_param)
        set_stim_onset(network_param, stim_onset)
        return network_param


#####################
# model selection
#####################
class ModelSelection:
    ''' Handles selection of models and allows analyzing them'''

    def __init__(self,
                 l6_config,
                 objectives_BAC=objectives_BAC,
                 objectives_step=objectives_step):
        self.l6_config = l6_config
        self.param_names = l6_config.biophysical_model_mdb[
            l6_config.biophysical_model_mdb_key]['params'].index
        self.pdf_XY_splitted, self.pdf_XY = self._get_pdfXY()
        self.objectives = [
            p for p in self.pdf_XY.columns if not p in self.param_names
        ]
        self.objectives_BAC = objectives_BAC
        self.objectives_step = objectives_step
        self.selected_models = []

    def _get_pdfXY(self):
        from biophysics_fitting.model_selection import get_model_pdf_from_mdb, get_pdf_selected
        pdf_XY_splitted, pdf_XY = get_model_pdf_from_mdb(
            self.l6_config.biophysical_model_mdb[
                self.l6_config.biophysical_model_mdb_key])
        return pdf_XY_splitted, pdf_XY

    import six

    def select_models(self, BAC_limit=3.5, step_limit=4.5):
        from biophysics_fitting.model_selection import get_model_pdf_from_mdb, get_pdf_selected
        selected_models = []
        for k, pdf in six.iteritems(self.pdf_XY_splitted):
            if not k in self.l6_config.runs:
                continue
            print(self.objectives_BAC)
            p, selected_model = get_pdf_selected(
                pdf,
                BAC_limit=BAC_limit,
                step_limit=step_limit,
                objectives_BAC=self.objectives_BAC,
                objectives_step=self.objectives_step)
            selected_models.append(selected_model)
            I.display.display(p)
        self.selected_models = selected_models
        return selected_models  # get_pdf_selected(pdf, BAC_limit = 3.5, step_limit = 4.5)

    def get_parameters(self, modelid):
        return self.pdf_XY.loc[modelid][self.param_names]

    def get_objectives(self, modelid, group='all'):
        '''group: all, BAC or step'''
        if group == 'all':
            o = self.objectives
        elif group == 'BAC':
            o = self.objectives_BAC
        elif group == 'step':
            o = self.objectives_step
        else:
            raise ValueError()
        return self.pdf_XY.loc[modelid][self.objectives]

    def get_cell_param(self,
                       modelid,
                       add_sim_param=False,
                       recordingSites=[],
                       tStop=295):
        simulator = self.get_simulator()
        cell_param = simulator.setup.get_cell_params(
            self.get_parameters(modelid))
        if add_sim_param:
            cell_param = _add_sim_to_neuron_param(cell_param,
                                                  recordingSites=recordingSites,
                                                  tStop=tStop)
        return cell_param

    def get_simulator(self):
        mdb = self.l6_config.mdb  # biophysical_model_mdb[self.l6_config.biophysical_model_mdb_key]
        return mdb['get_Simulator'](mdb)

    def get_cell_with_biophysics(self, modelid):
        return self.get_simulator().setup.get(self.get_parameters(modelid))


##################
# simulate and visualize model responses
###################
class o:
    '''object opaque for dask. Allows passing sumatra.NTParameter structures.
    They don't get serialized propely by dask otherwise'''

    def __init__(self, obj):
        self.obj = obj


def get_ax_ids(ll):
    '''takes list of list specifying the arangement of subplots.
    returns tuples, such that matplotlib axes are arranged in the same way
    
    ll = [['upper left','upper right'],['lower left','lower mid','lower right']]
    get_ax_ids(ll)
    {(2, 2, 1): 'upper left',
     (2, 2, 2): 'upper right',
     (2, 3, 4): 'lower left',
     (2, 3, 5): 'lower mid',
     (2, 3, 6): 'lower right'}
    '''
    return {
        (len(ll), len(line), linenr * len(line) + colnr + 1): col
        for linenr, line in enumerate(ll) for colnr, col in enumerate(line)
    }


class ModelResponses:

    def __init__(self, modelSelection):
        self.modelSelection = modelSelection

    def _save_cell(self, modelid, stim, cell):
        mdb = self.modelSelection.l6_config.mdb
        mdb = mdb.create_sub_mdb(modelid, raise_=False)
        mdb = mdb.create_sub_mdb('model_responses', raise_=False)
        mdb = mdb.create_sub_mdb(stim, raise_=False)
        mdb.setitem('cell', cell, dumper=I.dumper_cell)
        mdb.setitem('tVec', I.np.array(cell.tVec), dumper=I.dumper_numpy_to_npz)
        mdb.setitem('vmSoma',
                    I.np.array(cell.soma.recVList[0]),
                    dumper=I.dumper_numpy_to_npz)

    def _save_return_helper(self, cell, save, return_cell, modelid, stim):
        if save:
            self._save_cell(modelid, stim, cell)
        if return_cell:
            return cell

    @I.dask.delayed
    def simulate_current_stim(self,
                              modelid,
                              stim,
                              return_cell=False,
                              save=True):
        s = self.modelSelection.get_simulator()
        p = self.modelSelection.get_parameters(modelid)
        cell, _ = s.get_simulated_cell(p, stim)
        return self._save_return_helper(cell, save, return_cell, modelid, stim)

    @I.dask.delayed
    def simulate_synaptic_stim(self,
                               modelid,
                               network_param_o,
                               stim_description,
                               return_cell=False,
                               save=True,
                               tStop=2500):
        # dask does not serialize sumatra.NTParameterSet properly, therefore
        # we encapsulate it
        network_param = network_param_o.obj
        cell, _ = self.modelSelection.get_cell_with_biophysics(modelid)
        sim = I.scp.NTParameterSet({
            'tStart': 0.0,
            'tStop': tStop,
            'dt': 0.025,
            'Vinit': -75.0,
            'dt': 0.025,
            'T': 34.0
        })
        evokedNW = I.scp.NetworkMapper(cell, network_param.network, sim)
        evokedNW.create_saved_network2()
        I.scp.init_neuron_run(sim, vardt=False)
        return self._save_return_helper(cell, save, return_cell, modelid,
                                        stim_description)

    @I.dask.delayed
    def simulate_initialization(self, modelid, return_cell=False, save=True):
        cell, _ = self.modelSelection.get_cell_with_biophysics(modelid)
        sim = I.scp.NTParameterSet({
            'tStart': 0.0,
            'tStop': 300,
            'dt': 0.025,
            'Vinit': -75.0,
            'dt': 0.025,
            'T': 34.0
        })
        I.scp.init_neuron_run(sim, vardt=True)
        return self._save_return_helper(cell, save, return_cell, modelid,
                                        'init')

    def run_simulation_for_selected_models(self, client):
        selected_models = self.modelSelection.selected_models
        delayeds = [
            self.simulate_current_stim(modelid, stim)
            for modelid in selected_models
            for stim in self.modelSelection.get_simulator().setup.get_stims()
        ]
        delayeds.extend([
            self.simulate_initialization(modelid) for modelid in selected_models
        ])
        network_param = self.modelSelection.l6_config.get_network_param(
            loc='C2center', stim='C2', stim_onset=2000)
        delayeds.extend([
            self.simulate_synaptic_stim(modelid, o(network_param), 'PW_stim')
            for modelid in selected_models
        ])
        print(len(delayeds))
        futures = client.compute(delayeds)
        I.distributed.fire_and_forget(futures)
        return delayeds, futures

    def _extract_vm_from_cell(self, cell):
        '''helper function to extract membrane potential at 'important' locations'''
        l6_config = self.modelSelection.l6_config
        biophysical_model_mdb = l6_config.biophysical_model_mdb
        biophysical_model_mdb_key = l6_config.biophysical_model_mdb_key
        fixed_params = biophysical_model_mdb[biophysical_model_mdb_key][
            'fixed_params']
        BAC_dist = fixed_params['BAC.stim.dist']
        hot_zone_dist = fixed_params['hot_zone.max_'] * .5 + fixed_params[
            'hot_zone.max_'] * .5
        bAP_dist_1 = fixed_params['bAP.hay_measure.recSite1']
        bAP_dist_2 = fixed_params['bAP.hay_measure.recSite2']
        return {
            'soma':
                cell.soma.recVList[0],
            'hot_zone':
                biophysics_fitting.utils.vmApical(cell, hot_zone_dist),
            'bAP1':
                biophysics_fitting.utils.vmApical(cell, bAP_dist_1),
            'AIS': [s for s in cell.sections if s.label == 'AIS']
                   [1].recVList[-1]
            #'bAP2': biophysics_fitting.utils.vmApical(cell, 529)
        }

    def _plot_helper(self, cell, ax):
        colormap = I.defaultdict(lambda: 'grey')
        colormap['hot_zone'] = 'r'
        colormap['soma'] = 'k'
        colormap['AIS'] = 'g'
        import six
        for k, v in six.iteritems(self._extract_vm_from_cell(cell)):
            ax.plot(cell.tVec,
                    v,
                    label=k,
                    c=colormap[k],
                    alpha=.5 if k == 'AIS' else 1)

    def visualize_selected_models(self,
                                  ax_arrangement=[['PW_stim'],
                                                  ['BAC', 'bAP', 'init'],
                                                  [
                                                      'StepOne',
                                                      'StepTwo',
                                                      'StepThree',
                                                  ]],
                                  xlim={
                                      'BAC': (245, 400),
                                      'bAP': (245, 400)
                                  },
                                  ylim={'init': (-90, -60)}):
        selected_models = self.modelSelection.selected_models
        mdb = self.modelSelection.l6_config.mdb
        import six
        for model in selected_models:
            print(selected_models)
            m = mdb[str(model)]['model_responses']
            fig = I.plt.figure(figsize=(15 * 0.7, 12 * .7), dpi=200)
            for ax_position, stim in six.iteritems(get_ax_ids(ax_arrangement)):
                ax = fig.add_subplot(*ax_position)
                self._plot_helper(m[stim]['cell'], ax)
                ax.set_ylim(-90, 50)
                ax.set_title(stim)
                if stim in xlim:
                    ax.set_xlim(*xlim[stim])
                if stim in ylim:
                    ax.set_ylim(*ylim[stim])
            I.plt.tight_layout()
            I.sns.despine()
            I.display.display(fig)
            I.plt.close()


###################
# synaptic strength fitting
###################


def _add_sim_to_neuron_param(neuron_param, recordingSites=[], tStop=295):
    NTParameterSet = I.scp.NTParameterSet
    sim_param = {
        'tStart': 0.0,
        'tStop': 295,
        'dt': 0.025,
        'Vinit': -75.0,
        'dt': 0.025,
        'T': 34.0,
        'recordingSites': recordingSites
    }
    NMODL_mechanisms = {}
    return NTParameterSet({
        'neuron': neuron_param,
        'sim': sim_param,
        'NMODL_mechanisms': NMODL_mechanisms
    })


class SynapticStrengthFitting:

    def __init__(self, model_selection):
        self.model_selection = model_selection
        self.psps = I.defaultdict(dict)
        self._psp_descriptors = []
        self._psps = []
        self.neuron_param = None
        self.confile = None

    def run_synaptic_strength_fitting(self, client, loc='C2center'):
        mdb = self.model_selection.l6_config.mdb
        for model in self.model_selection.selected_models:
            if 'syn_strength_fitting' in list(mdb[model].keys()):
                print(
                    'skipping model {} as it seems to be simulated already. If the simulation '
                    .format(model))
                'run was incomplete, you can delete the data by running del l6_config.mdb[\'{}\'][\'{}\']'.format(
                    model, 'syn_strength_fitting')
                continue
            cell_param = self.model_selection.get_cell_param(model)
            cell_param = _add_sim_to_neuron_param(cell_param)
            confile = mdb['network_embedding'][loc].get_file('.con')
            self.confile = confile
            self.neuron_param = cell_param
            psp = I.simrun3.synaptic_strength_fitting.PSPs(cell_param, confile)
            if client is not None:
                psp.run(client)
            self.psps[model][loc] = psp

    import six

    def save_psps_to_mdb(self):
        mdb = self.model_selection.l6_config.mdb
        for model, psps in six.iteritems(self.psps):
            mdb[model].create_sub_mdb('syn_strength_fitting', raise_=False)
            for loc, psps in six.iteritems(psps):
                psps.get_voltage_and_timing()
                mdb[model]['syn_strength_fitting'][loc] = psps

    def get_psp_from_database(self, modelid, loc):
        mdb = self.model_selection.l6_config.mdb
        psp = mdb[modelid]['syn_strength_fitting'][loc]
        return psp

    def get_optimal_g(self,
                      model_id,
                      loc='C2center',
                      method='dynamic_baseline',
                      threashold=0.1):
        '''returns dataframe containing optimal synaptic strnghts. Assumes, that all voltage
        traces from synaptic strength fitting are saved in mdb[model_id][syn_strength_fitting_psp]'''

        #model_id = selected_models[0]
        psp = self.get_psp_from_database(model_id, loc)

        #### fix to add missing kwargs if old version has been pickled
        #### this could be entirely avoided if the version used for saving the object would be checked out in git
        #### to figure out the version, inspect the metadata saved in the model data base
        #### using mdb.metadata['your_key_to_your_PSP_object']
        kwargs = simrun3.utils.get_default_arguments(
            simrun3.synaptic_strength_fitting.PSPs.__init__)
        simrun3.utils.set_default_arguments_if_not_set(psp, kwargs)
        #### end of fix

        vt = psp.get_voltage_and_timing(method, merged=True)
        pdf = I.simrun3.synaptic_strength_fitting.ePSP_summary_statistics(
            vt, threashold=threashold)
        pdf_linfit = pdf.reset_index()
        pdf_linfit = pdf_linfit.groupby('celltype').apply(
            I.simrun3.synaptic_strength_fitting.linear_fit_pdf)
        pdf = I.pd.concat(
            [pdf_linfit, I.barrel_cortex.get_EPSP_measurement()], axis=1)
        I.simrun3.synaptic_strength_fitting.calculate_optimal_g(pdf)
        return pdf.rename(index={'VPM_C2': 'VPM'})

#     def visualize_psps(self, model_id, loc = 'C2center', g = 1.0, method = 'dynamic_baseline'):
#         psp = self.get_psp_from_database(model_id, loc)
#         vt = psp.get_voltage_and_timing(method)
#         #vt = I.simrun3.synaptic_strength_fitting.get_voltage_and_timing(vt, method)
#         vt = I.simrun3.synaptic_strength_fitting.merge_celltypes(vt)
#         pdf = I.pd.concat([I.pd.Series([x[1] for x in vt[name][g][g]], name = name)
#              for name in vt.keys()], axis = 1)
#         fig = I.plt.figure(figsize = (10,len(vt)*1.3))
#         ax = fig.add_subplot(111)
#         pdf.plot(kind = 'hist', subplots = True, bins = I.np.arange(0,pdf.max().max(), 0.01), ax = ax)

    def visualize_psps(self,
                       model_id,
                       loc='C2center',
                       method='dynamic_baseline',
                       g=1.0,
                       fig=None):
        psp = self.get_psp_from_database(model_id, loc)
        psp.visualize_psps(method=method, g=g, fig=None)

    def save_synapses_to_landmark_file(self,
                                       modelid,
                                       population,
                                       outfile,
                                       loc='C2center'):
        with I.silence_stdout:
            cell, _ = self.model_selection.get_cell_with_biophysics(modelid)
        network_param = self.model_selection.l6_config.get_network_param()
        nwMap = I.scp.NetworkMapper(cell, network_param.network,
                                    I.scp.NTParameterSet({'tStop': 10}))
        with I.silence_stdout:
            nwMap._assign_anatomical_synapses()
            nwMap._create_presyn_cells()
        syn_coordinates = [s.coordinates for s in cell.synapses[population]]
        I.scp.write_landmark_file(outfile, syn_coordinates)
        return syn_coordinates


############################################
# write landmark files
############################################


def write_landmark_file(model_selection):
    with I.silence_stdout:
        cell, _ = model_selection.get_cell_with_biophysics(
            model_selection.selected_models[0])

    fixed_params = model_selection.l6_config.mdb['fixed_params']

    landmark_positions = [
        biophysics_fitting.utils.vmApical_position(cell, dist=d) for d in [
            fixed_params['bAP.hay_measure.recSite1'],
            fixed_params['bAP.hay_measure.recSite2']
        ]
    ]

    I.scp.write_landmark_file(model_selection.l6_config.mdb['morphology']\
                              .join('recSites.landmarkAscii'), landmark_positions)


#############################################
# general method for setting up simulations of evoked activity
#############################################
class EvokedActivitySimulationSetup:

    def __init__(self,
                 output_dir_key=None,
                 synaptic_strength_fitting=None,
                 stims=None,
                 locs=None,
                 INHscalings=None,
                 tStim=245,
                 tEnd=295,
                 models=None):
        self.output_dir_key = output_dir_key
        self.synaptic_strength_fitting = synaptic_strength_fitting
        self.model_selection = synaptic_strength_fitting.model_selection
        self.l6_config = self.model_selection.l6_config
        self.stims = stims
        self.locs = locs
        self.INHscaling = INHscalings
        self.tStim = tStim
        self.tEnd = tEnd
        self.ds = []
        self.futures = None
        self.models = models
        if self.models is None:
            self.models = self.synaptic_strength_fitting.model_selection.selected_models

    def setup(self):
        mdb = self.l6_config.mdb

        for model_id in self.models:
            syn_strength = self.synaptic_strength_fitting.get_optimal_g(
                model_id)['optimal g']
            print('syn_strength')
            I.display.display(syn_strength)
            if not self.output_dir_key in list(mdb[str(model_id)].keys()):
                mdb[str(model_id)].create_managed_folder(self.output_dir_key)
            else:
                print(
                    'skipping model {} as it seems to be simulated already. If the simulation '
                    .format(model_id))
                'run was incomplete, you can delete the data by running del l6_config.mdb[\'{}\'][\'{}\']'.format(
                    model_id, self.output_dir_key)
                continue
            landmark_name = mdb['morphology'].join('recSites.landmarkAscii')
            cell_param = self.model_selection.get_cell_param(
                model_id, add_sim_param=True, recordingSites=[landmark_name])
            cell_param_name = mdb[str(model_id)]['PW_fitting'].join(
                'cell.param')
            cell_param.save(cell_param_name)
            for INH_scaling in self.INHscaling:
                for stim in self.stims:
                    for loc in self.locs:
                        network_param = self.l6_config.get_network_param(
                            stim=stim, loc=loc, stim_onset=self.tStim)
                        I.scp.network_param_modify_functions.change_evoked_INH_scaling(
                            network_param, INH_scaling)
                        I.scp.network_param_modify_functions.change_glutamate_syn_weights(
                            network_param, syn_strength)
                        network_param_name = mdb[str(model_id)][
                            self.output_dir_key].join(
                                'network_INH_{}_stim_{}_loc_{}.param'.format(
                                    INH_scaling, stim, loc))
                        network_param.save(network_param_name)
                        outdir = mdb[str(model_id)][self.output_dir_key].join(
                            str(INH_scaling)).join(stim).join(str(loc))
                        print(model_id, INH_scaling, stim, loc)
                        d = I.simrun_run_new_simulations(
                            cell_param_name,
                            network_param_name,
                            dirPrefix=outdir,
                            nSweeps=200,
                            nprocs=1,
                            scale_apical=lambda x: x,
                            silent=False,
                            tStop=self.tEnd)
                        self.ds.append(d)

    def run(self, client, fire_and_forget=False):
        if len(self.ds) == 0:
            raise RuntimeError("You must run the setup method first")
        self.futures = client.compute(self.ds)
        if fire_and_forget:
            I.distributed.fire_and_forget(self.futures)

    def init_mdb(self, client, dendritic_voltage_traces=False):
        mdb = self.l6_config.mdb
        for model_id in self.model_selection.selected_models:
            mdb_key = self.output_dir_key + '_mdb'
            if mdb_key in list(mdb[str(model_id)].keys()):
                del mdb[str(model_id)][mdb_key]
            if not mdb_key in list(mdb[str(model_id)].keys()):
                mdb_init = mdb[str(model_id)].create_sub_mdb(mdb_key)
                I.mdb_init_simrun_general.init(
                    mdb_init,
                    mdb[str(model_id)][self.output_dir_key],
                    burst_times=False,
                    get=client.get,
                    dendritic_voltage_traces=dendritic_voltage_traces)


class EvokedActivitySimulationSetupRieke:

    def __init__(self,
                 output_dir_key=None,
                 synaptic_strength_fitting=None,
                 stims=None,
                 locs=None,
                 INHscalings=None,
                 ongoing_scales=(1,),
                 ongoing_scales_pop=I.inhibitory,
                 custom_glutamate_conductances=None,
                 nProcs=1,
                 nSweeps=200,
                 cell_param_modify_functions=[],
                 network_param_modify_functions=[],
                 tStim=245,
                 tEnd=295,
                 models=None):
        self.output_dir_key = output_dir_key
        self.synaptic_strength_fitting = synaptic_strength_fitting
        self.model_selection = synaptic_strength_fitting.model_selection
        self.l6_config = self.model_selection.l6_config
        self.stims = stims
        self.locs = locs
        self.INHscaling = INHscalings
        self.ongoing_scales = ongoing_scales  #rieke
        self.ongoing_scales_pop = ongoing_scales_pop
        self.custom_glutamate_conductances = custom_glutamate_conductances  # should be pandas dataframe or series
        self.cell_param_modify_functions = cell_param_modify_functions
        self.network_param_modify_functions = network_param_modify_functions
        self.nProcs = nProcs
        self.nSweeps = nSweeps  # /rieke
        self.tStim = tStim
        self.tEnd = tEnd
        self.ds = []
        self.futures = None
        self.models = models
        if self.models is None:
            self.models = self.synaptic_strength_fitting.model_selection.selected_models

    def setup(self):
        mdb = self.l6_config.mdb

        for model_id in self.models:
            if self.custom_glutamate_conductances is None:
                syn_strength = self.synaptic_strength_fitting.get_optimal_g(
                    model_id)['optimal g']
                print('syn_strength')
                I.display.display(syn_strength)
            elif not self.custom_glutamate_conductances is None:
                syn_strength = self.custom_glutamate_conductances

            if not self.output_dir_key in list(mdb[str(model_id)].keys()):
                mdb[str(model_id)].create_managed_folder(self.output_dir_key)
            else:
                print(
                    'skipping model {} as it seems to be simulated already. If the simulation '
                    .format(model_id) +
                    'run was incomplete, you can delete the data by running del l6_config.mdb[\'{}\'][\'{}\']'
                    .format(model_id, self.output_dir_key))
                continue
            landmark_name = mdb['morphology'].join('recSites.landmarkAscii')
            cell_param = self.model_selection.get_cell_param(
                model_id, add_sim_param=True, recordingSites=[landmark_name])
            cell_param_name = mdb[str(model_id)][self.output_dir_key].join(
                'cell.param')
            for cell_param_modify_function in self.cell_param_modify_functions:
                cell_param_modify_function(cell_param)

            cell_param.save(cell_param_name)
            for INH_scaling in self.INHscaling:
                for ongoing_scale in self.ongoing_scales:
                    for stim in self.stims:
                        for loc in self.locs:
                            network_param = self.l6_config.get_network_param(
                                stim=stim, loc=loc, stim_onset=self.tStim)
                            I.scp.network_param_modify_functions.change_evoked_INH_scaling(
                                network_param, INH_scaling)
                            I.scp.network_param_modify_functions.change_glutamate_syn_weights(
                                network_param, syn_strength)
                            I.scp.network_param_modify_functions.change_ongoing_interval(
                                network_param,
                                factor=ongoing_scale,
                                pop=self.ongoing_scales_pop
                            )  ##adjust ongoing activity if necessary
                            for network_param_modify_function in self.network_param_modify_functions:
                                network_param_modify_function(network_param)
                            network_param_name = mdb[str(
                                model_id
                            )][self.output_dir_key].join(
                                'network_INHevoked_{}_INHongoing_{}_stim_{}_loc_{}.param'
                                .format(INH_scaling, ongoing_scale, stim, loc))
                            network_param.save(network_param_name)
                            outdir = mdb[str(
                                model_id)][self.output_dir_key].join(
                                    str(ongoing_scale)).join(
                                        str(INH_scaling)).join(stim).join(
                                            str(loc))
                            print(model_id, ongoing_scale, INH_scaling, stim,
                                  loc)

                            d = I.simrun_run_new_simulations(
                                cell_param_name,
                                network_param_name,
                                dirPrefix=outdir,
                                nSweeps=self.nSweeps,
                                nprocs=self.nProcs,
                                scale_apical=lambda x: x,
                                silent=False,
                                tStop=self.tEnd)
                            self.ds.append(d)

    def run(self, client, fire_and_forget=False):
        if len(self.ds) == 0:
            raise RuntimeError("You must run the setup method first")
        self.futures = client.compute(self.ds)
        if fire_and_forget:
            I.distributed.fire_and_forget(self.futures)

    def init_mdb(self, client, dendritic_voltage_traces=False):
        mdb = self.l6_config.mdb
        for model_id in self.model_selection.selected_models:
            mdb_key = self.output_dir_key + '_mdb'
            if mdb_key in list(mdb[str(model_id)].keys()):
                del mdb[str(model_id)][mdb_key]
            if not mdb_key in list(mdb[str(model_id)].keys()):
                mdb_init = mdb[str(model_id)].create_sub_mdb(mdb_key)
                I.mdb_init_simrun_general.init(
                    mdb_init,
                    mdb[str(model_id)][self.output_dir_key],
                    burst_times=False,
                    get=client.get,
                    dendritic_voltage_traces=dendritic_voltage_traces)


############
# PW fitting
############


def signchange(x, y):
    if x / abs(x) == y / abs(y):
        return False
    else:
        return True


assert signchange(-2, 1)
assert ~signchange(2, 1)
assert ~signchange(-22, -1)
assert signchange(22, -1789)


def linear_interpolation_between_pairs(X, Y, x):
    #     assert x<=max(X)
    #     assert x>=min(X)
    #     pair = [lv for lv in range(len(X)-1) if signchange(X[lv]-x, X[lv+1]-x)]
    #     assert len(pair) == 1
    #     pair = pair[0]
    #     m = (Y[pair+1]-Y[pair]) / (X[pair+1]-X[pair])
    #     c = Y[pair]-X[pair]*m
    #     return m*x+c
    X = I.np.asarray(X)
    if float(x) in X.astype('float'):  # if the value already exists
        result = Y[I.np.where(X == x)[0][0]]
    else:
        pair = [lv for lv in range(len(X) - 1) if X[lv] < x < X[lv + 1]]

        assert len(pair) == 1
        pair = pair[0]
        m = (Y[pair + 1] - Y[pair]) / (X[pair + 1] - X[pair])
        c = Y[pair] - X[pair] * m

        result = m * x + c
    return result


class PWfitting:

    def __init__(
            self,
            l6_config,
            model_selection,
            min_time=8,
            max_time=25,
            mdb_path1='/nas1/Data_arco/results/20190114_spiketimes_database',
            mdb_path2='/nas1/Data_arco/results/mdb_robert_3x3/',
            stim='D2',
            cellid=None):
        self.l6_config = l6_config
        self.model_selection = model_selection
        self.min_time = min_time
        self.max_time = max_time
        self.mdb_path1 = mdb_path1
        self.mdb_path2 = mdb_path2
        self.stim = stim
        if cellid == None:
            self.cellid = l6_config.biophysical_model_mdb_key
        else:
            self.cellid = cellid
        ### get target value
        #st_CDK = I.ModelDataBase('/nas1/Data_arco/results/20190114_spiketimes_database')['CDK_PassiveTouch'] # rieke
        st_CDK = I.ModelDataBase(self.mdb_path1)['CDK_PassiveTouch']

        st_CDK = I.select(st_CDK, stim=self.stim)  #changed by rieke
        self.CDK_target_value_avg_L5tt = I.temporal_binning(st_CDK,
                                                            min_time=min_time,
                                                            max_time=max_time,
                                                            bin_size=max_time -
                                                            min_time)[1][0]
        self.CDK_target_value_same_cell = I.temporal_binning(
            I.select(st_CDK, cell=self.cellid),
            min_time=min_time,
            max_time=max_time,
            bin_size=max_time - min_time)[1][0]

        print('CDK_target_value_avg_L5tt: {:s}'.format(
            self.CDK_target_value_avg_L5tt))
        print('CDK_target_value_same_cell: {:s}'.format(
            self.CDK_target_value_same_cell))

        #st_robert_control = I.ModelDataBase('/nas1/Data_arco/results/mdb_robert_3x3/')['spike_times']
        st_robert_control = I.ModelDataBase(self.mdb_path2)['spike_times']

        st_robert_control = st_robert_control[st_robert_control.index.str.split(
            '_').str[0] == 'C2']
        self.target_robert = I.temporal_binning(st_robert_control,
                                                min_time=245 + min_time,
                                                max_time=245 + max_time,
                                                bin_size=max_time -
                                                min_time)[1][0]
        print('target_robert: {:s}'.format(self.target_robert))

    def _get_INH_dependent_n_spikes(self, model):
        st = self.l6_config.mdb[str(model)]['PW_fitting_mdb']['spike_times']
        st['INH'] = st.index.str.split('/').str[0]
        fun = lambda x: I.temporal_binning(x,
                                           min_time=245 + self.min_time,
                                           max_time=245 + self.max_time,
                                           bin_size=self.max_time - self.
                                           min_time)[1][0]
        s = st.groupby('INH').apply(fun)
        s.name = model
        return s

    def plot_INH_pspike_relationship(self):

        colors = ['k', 'r', 'b', 'g', 'orange', 'pink']
        model_color = [[
            model, colors[lv]
        ] for lv, model in enumerate(self.model_selection.selected_models)]
        for m, c in model_color:
            s = self._get_INH_dependent_n_spikes(m)
            I.plt.plot(s.index, s, 'o', c=c, label=str(m))
        I.plt.axhline(self.CDK_target_value_avg_L5tt, color='k')
        I.plt.axhline(self.CDK_target_value_same_cell)
        I.plt.axhline(self.target_robert)
        I.plt.xticks(s.index.astype('f'))
        I.plt.xlabel('INH')
        I.plt.ylabel('spikes per trial 0-25ms poststim')
        I.plt.legend()
        I.sns.despine()

    def get_INH_scaling_dict(self):
        INH_scaling_dict = {}
        for model in self.model_selection.selected_models:
            try:
                s = self._get_INH_dependent_n_spikes(model)
                INH_scaling_dict[model] = linear_interpolation_between_pairs(
                    s.astype('float'), s.index.astype('float'),
                    self.CDK_target_value_avg_L5tt)
            except AssertionError:
                pass
        return INH_scaling_dict

    def _plot_PSTHs(self,
                    INH,
                    CDK_PW=True,
                    robert=True,
                    models=True,
                    plottype='hist'):
        mdb = self.l6_config.mdb
        if plottype == 'hist':
            plotfun = I.histogram
        elif plottype == 'line':

            def plotfun(bins, label=None, fig=None, colormap=None):
                fig.plot(bins[0][:-1],
                         bins[1],
                         color=colormap[label],
                         label=label)

        st_CDK = I.ModelDataBase(self.mdb_path1)['CDK_PassiveTouch']
        st_CDK = I.select(st_CDK, stim='D2')
        CDK_bins = I.temporal_binning(st_CDK,
                                      min_time=-144,
                                      max_time=100,
                                      bin_size=1)
        CDK_bins = [list(range(245 - 144, 245 + 100 + 1)), CDK_bins[1]]
        st_robert_control = I.ModelDataBase(self.mdb_path2)['spike_times']
        st_robert_control = st_robert_control[st_robert_control.index.str.split(
            '_').str[0] == 'C2']
        robert_bins = I.temporal_binning(st_robert_control,
                                         min_time=0,
                                         max_time=245 + 50,
                                         bin_size=1)
        cmap = I.defaultdict(lambda: None)
        cmap['CDK_PW'] = 'grey'
        cmap['robert'] = 'blue'
        fig = I.plt.figure(figsize=(15, 3))
        if CDK_PW:
            plotfun(CDK_bins,
                    label='CDK_PW',
                    fig=fig.add_subplot(111),
                    colormap=cmap)
        if robert:
            plotfun(robert_bins,
                    label='robert',
                    fig=fig.add_subplot(111),
                    colormap=cmap)

        if models:
            for model in self.model_selection.selected_models:
                st = mdb[str(model)]['PW_fitting_mdb']['spike_times']
                st = st[st.index.str.split('/').str[0] == str(INH)]
                plotfun(I.temporal_binning(st, min_time=0, max_time=350),
                        fig=fig.add_subplot(111),
                        label=str(model),
                        colormap=cmap)
        I.plt.ylim([0, 0.3])
        I.plt.title(str(INH))
        I.plt.legend()
        return fig

    def plot_PSTHs(self):
        for INH in I.np.arange(0.5, 2.1, .1):
            self._plot_PSTHs(INH, CDK_PW=True, robert=True)


def get_all_L6_simulation_dbs():
    mdb = I.ModelDataBase(
        '/nas1/Data_arco/results/20190507_metaanalysis_of_L6_control_experiments'
    )
    # create mdb dict
    mdbs = {}
    for k in list(mdb.keys()):
        if k == 'local':
            continue
        m = mdb[k]
        l6_config = m['l6_config']
        selected_models = m['selected_models']
        for model in selected_models:
            model_run = model.split('_')[-3]
            morphology = k.split('_')[4]
            try:
                m = l6_config.mdb[model]['3x3_control_mdb']
            except:
                print('skipping ', morphology, model_run)
                continue
            mdbs[str(model_run) + '_' + str(morphology)] = m
    return mdbs


#####
# unused so far

# def setup_cell_synaptic_input(cell, network_param, sim_param):
#     evokedNW = I.scp.NetworkMapper(cell, network_param.network, sim_param)
#     evokedNW.create_saved_network2()
#     return evokedNW
#
# def setup_cell_synaptic_input_PW(cell, param_modfuns = []):
#     from sumatra.parameters import NTParameterSet
#     network_param = get_network_param()
#     for fun in param_modfuns:
#         fun(network_param)
#     sim_param = NTParameterSet(dict(tStop = 2500))
#     setup_cell_synaptic_input(cell, network_param, sim_param)
#
# def get_param_by_modelid(mdb, modelid):
#     param_names = mdb['params'].index
#     return pdf_XY.loc[modelid][param_names]
#
# def get_cell_with_biophysics(m, modelid):
#     s = m['get_Simulator'](m)
#     param = get_param_by_modelid(m, modelid)
#     cell, param = s.setup.get(param)
#     return cell
#
# @I.dask.delayed
# def simulate(mdb, modelid, savemdb = None, cell_setup_fun = lambda x: x,
#              tStop = 300, vardt = False, return_cell = False, cell_param_mod_fun = None):
#     cell = get_cell_with_biophysics(mdb, modelid)
#     if cell_param_mod_fun is not None:
#         raise NotImplementedError()
#         cell_param_mod_fun(cell_param)
#     cell_setup_fun(cell)
#     sim = I.scp.NTParameterSet({'tStart': 0.0, 'tStop': tStop, 'dt': 0.025, 'Vinit': -75.0, 'dt': 0.025, 'T': 34.0})
#     I.scp.init_neuron_run(sim, vardt = vardt)
#     if savemdb is not None:
#         savemdb.setitem('cell', cell, dumper = I.dumper_cell)
#         savemdb.setitem('tVec', I.np.array(cell.tVec), dumper = I.dumper_numpy_to_npz)
#         savemdb.setitem('vmSoma', I.np.array(cell.soma.recVList[0]), dumper = I.dumper_numpy_to_npz)
#     if return_cell:
#         return cell
#     else:
#         return I.np.array(cell.tVec), I.np.array(cell.soma.recVList[0])
#

####################################
# reproduce figure 2
####################################

# general functions for saving grouped landmarks
import os


def fig2_grouping_function_celltype(x):
    return x.split('_')[0]


def fig2_grouping_function_EI(x):
    celltype = fig2_grouping_function_celltype(x)
    if celltype in I.excitatory:
        return 'EXC'
    elif celltype in I.inhibitory:
        return 'INH'
    else:
        return 'unknown'


def fig2_grouping_function_TC_IC(x):
    celltype = fig2_grouping_function_celltype(x)
    if celltype == 'VPM':
        return 'TC'
    elif celltype in I.excitatory:
        return 'IC'
    elif celltype in I.inhibitory:
        return 'INH'
    else:
        return 'unknown'


def save_pdf_to_landmarkfile(pdf, path):
    I.scp.write_landmark_file(path, \
                             [x[1].values for x in pdf.iterrows()])


def save_fractions_of_landmark_pdf(pdf,
                                   outdir,
                                   fracs=[0.005, 0.01, 0.05],
                                   grouping=[
                                       fig2_grouping_function_celltype,
                                       fig2_grouping_function_EI,
                                       fig2_grouping_function_TC_IC
                                   ]):
    for grouping_fun in grouping:
        for frac in fracs:
            landmarks_pdf_frac = pdf.sample(frac=frac)
            grouping_column = landmarks_pdf_frac.label.apply(grouping_fun)
            path = os.path.join(outdir, str(frac))
            if not os.path.exists(path):
                os.makedirs(path)
            for name, group in landmarks_pdf_frac.groupby(grouping_column):
                outpath = I.os.path.join(path, name + '.landmarkAscii')
                I.scp.write_landmark_file(outpath, list(group.positions))


# Panel A
amira_view = '''
viewer 0 setCameraOrientation 0.391947 0.679242 0.62049 2.37879
viewer 0 setCameraPosition 1509.44 802.209 -489.014
viewer 0 setCameraFocalDistance 1579.11
viewer 0 setCameraNearDistance -705.091
viewer 0 setCameraFarDistance 3502.41
viewer 0 setCameraType orthographic
viewer 0 setCameraHeight 2485.99
'''

somaloc_bc = I.os.path.join(I.os.path.dirname(__file__),
                            'reproducing_L6paper_data', 'all_soma_locations',
                            'BC')

somaloc_vpm = I.os.path.join(I.os.path.dirname(__file__),
                             'reproducing_L6paper_data', 'all_soma_locations',
                             'VPM')

whole_bc_syn = I.os.path.join(I.os.path.dirname(__file__),
                              'reproducing_L6paper_data', 'whole_bc_embedding',
                              'full_bc_embedding.syn')

whole_bc_con = I.os.path.join(I.os.path.dirname(__file__),
                              'reproducing_L6paper_data', 'whole_bc_embedding',
                              'full_bc_embedding.con')

anatomy_folder = I.os.path.join(I.os.path.dirname(__file__),
                                'reproducing_L6paper_data', 'anatomy')

amira_template_folder = I.os.path.join(I.os.path.dirname(__file__),
                                       'reproducing_L6paper_data',
                                       'amira_templates')


def get_fraction_of_landmarkAscii(frac, path):
    'returns fraction of landmarkAscii files defined in path'
    f = I.os.path.basename(path)
    #print path
    celltype = f.split('.')[-2]
    positions = I.scp.read_landmark_file(path)
    pdf = I.pd.DataFrame({'positions': positions, 'label': celltype})
    if len(pdf) == 0:  # cannot sample from empty pdf
        return pdf
    if frac >= 1:
        return pdf
    else:
        return pdf.sample(frac=frac)


def get_fraction_of_landmarkAscii_dir(frac, basedir=None):
    'loads all landmarkAscii files in directory and returns dataframe containing'\
    'position and filename (without suffix i.e. without .landmarkAscii)'
    out = []
    for f in I.os.listdir(basedir):
        if not f.endswith('landmarkAscii'):
            continue
        out.append(get_fraction_of_landmarkAscii(1, I.os.path.join(basedir, f)))
    #if frac >= 1:
    #        return I.pd.concat(out).sort_values('label').reset_index(drop = True)
    #else:
    return I.pd.concat(out).sample(frac=frac).sort_values('label').reset_index(
        drop=True)


get_fraction_of_all_bc_cells = lambda frac: get_fraction_of_landmarkAscii_dir(
    frac, somaloc_bc)


def get_fraction_of_all_vpm_cells(frac):
    pdf = get_fraction_of_landmarkAscii_dir(frac, somaloc_vpm)
    pdf.label = pdf.label.apply(lambda x: 'VPM_' + x.split('_')[-1])
    pdf = pdf[pdf.label.apply(lambda x: not 'row' in x)]
    return pdf


get_fraction_of_all_cells = lambda frac: I.pd.concat(
    [get_fraction_of_all_bc_cells(frac),
     get_fraction_of_all_vpm_cells(frac)])

#def get_soma_positions_by_celltype(celltype):
#    basedir = I.os.path.dirname(__file__)
#    basedir = I.os.path.join(basedir, 'reproducing_L6paper_data')
#    path = I.os.path.join(basedir, celltype) + '.landmarkAscii'
#    return I.scp.read_landmark_file(path)

import singlecell_input_mapper.singlecell_input_mapper.writer as writer


def write_embedding_from_pdf(pdf, dirname, fname):
    '''This takes a dataframe of the format:
    
                    label, position
                    
    position is a 3-tuple (x,y,z)
    
    and saves it as syn and con file at the folder fname.'''
    if not I.os.path.exists(fname):
        I.os.makedirs(fname)
    out = []
    for name, df in pdf.groupby('label'):
        df = I.pd.DataFrame({
            'type': name,
            'cellid': list(range(len(df))),
            'positions': df.positions
        })
        out.append(df)
    functionalMap = functionalMap_pdf = I.pd.concat(out)
    functionalMap = [(row.type, row.cellid, row.cellid)
                     for row in functionalMap.itertuples()]
    writer.write_anatomical_realization_map(
        I.os.path.join(dirname, fname + '.con'), functionalMap, 'test.syn')
    synapses = [(x[0], 1, 0.5) for x in functionalMap]
    writer.write_cell_synapse_locations(I.os.path.join(dirname, fname + '.syn'),
                                        {'synType': synapses}, 'test.syn')
    functionalMap_pdf['x'] = functionalMap_pdf.positions.apply(lambda x: x[0])
    functionalMap_pdf['y'] = functionalMap_pdf.positions.apply(lambda x: x[1])
    functionalMap_pdf['z'] = functionalMap_pdf.positions.apply(lambda x: x[2])
    return functionalMap_pdf.drop('positions',
                                  axis=1).set_index(['type', 'cellid'])


def create_whole_bc_embedding(outdir):
    '''creates syn- and confile for an embedding of whole barrel cortex'''
    return write_embedding_from_pdf(get_fraction_of_all_cells(1), outdir,
                                    'full_bc_embedding')


def get_cellNr(network_param):
    return {
        celltype: network_param.network[celltype].cellNr
        for celltype in list(network_param.network.keys())
    }


def get_landmarks_pdf_by_cellNr(network_param, landmarks_pdf_all):
    cellnr = get_cellNr(network_param)
    groups = {name: group for name, group in landmarks_pdf_all.groupby('label')}
    out = []
    for celltype in list(cellnr.keys()):
        if not celltype in list(groups.keys()):
            print((
                'skipping celltype {} as it is not part of the barrel cortex model'
                .format(celltype)))
            continue
        if cellnr[celltype] > len(groups[celltype]):
            print('specified cellnr {} is larger '.format(cellnr[celltype]) + \
                  'than number of cells {} of type {}. Using {} cells'.format(len(groups[celltype]),
                                                                              celltype,
                                                                              len(groups[celltype])))
            sample = groups[celltype]
        else:
            sample = groups[celltype].sample(cellnr[celltype])
        out.append(sample)
    return I.pd.concat(out)


load_param_files_from_mdb = I.mdb_init_simrun_general.load_param_files_from_mdb


def write_hoc_with_0_soma_diameter(hocpath_in, hocpath_out):
    out = []
    with open(I.resolve_mdb_path(hocpath_in)) as f:
        in_soma = False
        for line in f.readlines():
            if '{create soma}' in line:
                in_soma = True
            if len(line.strip()) == 0:
                in_soma = False
            if in_soma and ('pt3dadd' in line):
                line = line.strip('pt3add{}()').split(',')
                line = '{pt3dadd(' + line[0] + ',' + line[1] + ',' + line[
                    2] + ',0)}'
            out.append(line.strip())
    with open(I.resolve_mdb_path(hocpath_out), 'w') as f:
        f.write('\n'.join(out))


# function for saving fig2b
def get_synapse_landmarks_pdf(mdb, sti):
    neup, netp = I.load_param_files_from_mdb(mdb, sti)
    cell = I.scp.create_cell(neup.neuron)
    evokedNW = I.scp.NetworkMapper(cell, netp.network, simParam=neup.sim)
    evokedNW._assign_anatomical_synapses()
    out = []
    import six
    for k, synlist in six.iteritems(cell.synapses):
        for syn in synlist:
            out.append((k, syn.coordinates))
    cell.re_init_cell()
    evokedNW.re_init_network()
    return I.pd.DataFrame(out, columns=['label', 'positions'])


def fig2a_anatomical_embedding(mdb,
                               sti,
                               outdir,
                               cells=True,
                               synapses=True,
                               fracs=[0.005, 0.01, 0.05, 0.1, 0.5, 1],
                               frac_all_cells_selected=0.05,
                               frac_presynaptic_cells_selected=0.05,
                               frac_synapses_selected=0.1):
    # grab all cells
    # save them to all_cells/frac_0.005
    if I.os.path.exists(outdir):
        print('warning! the specified directory already exists!')
        #I.shutil.rmtree(outdir)
    if cells:
        neup, netp = load_param_files_from_mdb(mdb, sti)
        landmarks_pdf_all = get_fraction_of_all_cells(1)
        save_fractions_of_landmark_pdf(landmarks_pdf_all,
                                       outdir + '/all_cells',
                                       fracs=fracs)
        # I.os.makedirs(outdir + '/all_cells' + '/selected')
        I.shutil.copytree(
            outdir + '/all_cells' + '/{}'.format(frac_all_cells_selected),
            outdir + '/all_cells' + '/selected')
        landmarks_pdf_presynaptic = get_landmarks_pdf_by_cellNr(
            netp, landmarks_pdf_all)
        save_fractions_of_landmark_pdf(landmarks_pdf_presynaptic,
                                       outdir + '/presynaptic_cells',
                                       fracs=fracs)
        # I.os.makedirs(outdir + '/presynaptic_cells' + '/selected')
        I.shutil.copytree(
            outdir + '/presynaptic_cells' +
            '/{}'.format(frac_presynaptic_cells_selected),
            outdir + '/presynaptic_cells' + '/selected')
        #if I.os.path.exists(outdir + '/anatomy'):
        #    I.shutil.rmtree(outdir + '/anatomy')
        I.shutil.copytree(anatomy_folder, outdir + '/anatomy')
        I.shutil.copy(amira_template_folder + '/Presynaptic_Cells.hx', outdir)
    I.shutil.copy(I.resolve_mdb_path(neup.neuron.filename),
                  outdir + '/anatomy/morphology.hoc')
    write_hoc_with_0_soma_diameter(outdir + '/anatomy/morphology.hoc',
                                   outdir + '/anatomy/morphology_no_soma.hoc')
    if synapses:
        with I.silence_stdout:
            landmarks_synapses = get_synapse_landmarks_pdf(mdb, sti)
        save_fractions_of_landmark_pdf(landmarks_synapses,
                                       outdir + '/all_synapses',
                                       fracs=fracs)
        # I.os.makedirs(outdir + '/all_synapses' + '/selected')
        I.shutil.copytree(
            outdir + '/all_synapses' + '/{}'.format(frac_synapses_selected),
            outdir + '/all_synapses' + '/selected')
        I.shutil.copy(amira_template_folder + '/Synapses.hx', outdir)


# Panel B


def select_cells_that_spike_in_interval(sa,
                                        tmin,
                                        tmax,
                                        set_index=[
                                            'synapse_ID', 'synapse_type'
                                        ]):
    pdf = sa.set_index(list(set_index))
    pdf = pdf[[c for c in pdf.columns if c.isdigit()]]
    pdf = pdf[((pdf >= tmin) & (pdf < tmax)).any(axis=1)]
    cells_that_spike = pdf.index
    cells_that_spike = cells_that_spike.tolist()
    return cells_that_spike


def fig2b_functional_embedding(mdb,
                               sti,
                               outdir,
                               cells=True,
                               synapses=True,
                               min_time=245,
                               max_time=245 + 25,
                               fracs=[0.005, 0.01, 0.05, 0.1, 0.5, 1],
                               frac_presynaptic_cells_selected=0.5,
                               frac_synapses_selected=0.1):
    # grab all cells
    # save them to all_cells/frac_0.005
    if I.os.path.exists(outdir):
        print('warning! the specified directory already exists!')
        # I.shutil.rmtree(outdir)
    neup, netp = load_param_files_from_mdb(mdb, sti)
    if cells:
        landmarks_pdf_all = get_fraction_of_all_cells(1)
        landmarks_pdf_presynaptic = landmarks_pdf_all.groupby('label').apply(
            lambda x: x.reset_index(drop=True))
        ca = mdb['cell_activation'].loc[sti].compute()
        selection = select_cells_that_spike_in_interval(
            ca,
            min_time,
            max_time,
            set_index=['presynaptic_cell_type', 'cell_ID'])
        selection_missing = [
            s for s in selection if not s in landmarks_pdf_presynaptic.index
        ]
        selection = [
            s for s in selection if s in landmarks_pdf_presynaptic.index
        ]
        if selection_missing:
            print("couldnb't find presynaptic cells for", selection_missing)
        landmarks_pdf_presynaptic = landmarks_pdf_presynaptic.loc[
            selection].dropna()

        #save_fractions_of_landmark_pdf(landmarks_pdf_all, outdir + '/all_cells',
        #                               fracs = fracs)
        save_fractions_of_landmark_pdf(landmarks_pdf_presynaptic,
                                       outdir + '/presynaptic_cells',
                                       fracs=fracs)
        # I.os.makedirs(outdir + '/presynaptic_cells' + '/selected')
        I.shutil.copytree(
            outdir + '/presynaptic_cells' +
            '/{}'.format(frac_presynaptic_cells_selected),
            outdir + '/presynaptic_cells' + '/selected')
        #if I.os.path.exists(outdir + '/anatomy'):
        #    I.shutil.rmtree(outdir + '/anatomy')
        I.shutil.copytree(anatomy_folder, outdir + '/anatomy')
        I.shutil.copy(amira_template_folder + '/Presynaptic_Cells.hx', outdir)
    I.shutil.copy(I.resolve_mdb_path(neup.neuron.filename),
                  outdir + '/anatomy/morphology.hoc')
    write_hoc_with_0_soma_diameter(outdir + '/anatomy/morphology.hoc',
                                   outdir + '/anatomy/morphology_no_soma.hoc')
    if synapses:
        with I.silence_stdout:
            landmarks_synapses = get_synapse_landmarks_pdf(mdb, sti)
        sa = mdb['synapse_activation'].loc[sti].compute()
        selection = select_cells_that_spike_in_interval(
            sa, min_time, max_time, set_index=['synapse_type', 'synapse_ID'])
        landmarks_synapses = landmarks_synapses.groupby('label').apply(
            lambda x: x.reset_index(drop=True))
        landmarks_synapses = landmarks_synapses.loc[selection]
        save_fractions_of_landmark_pdf(landmarks_synapses,
                                       outdir + '/all_synapses',
                                       fracs=fracs)
        # I.os.makedirs(outdir + '/all_synapses' + '/selected')
        I.shutil.copytree(
            outdir + '/all_synapses' + '/{}'.format(frac_synapses_selected),
            outdir + '/all_synapses' + '/selected')
        I.shutil.copy(amira_template_folder + '/Synapses.hx', outdir)


# Video S1


# Panel C
@I.dask.delayed
def _fig2C_data_step1(sa_pd,
                      ongoing_min_time=None,
                      ongoing_max_time=None,
                      evoked_min_time=None,
                      evoked_max_time=None,
                      PC=None,
                      SCs=None,
                      celltype_group_fun=None):
    '''returns the dataframe required for reproducing plot Fig2C.
    Requires a pandas data frame. Use fig2C_data to compute from a dask dataframe.'''
    sa = sa_pd

    def map_fun(x):
        if x in PC:
            return 'PC'
        if x in SCs:
            return 'SC'
        return '2ndSC'

    sa['SC'] = sa.synapse_type.str.split('_').str[1].map(map_fun)
    sa['celltype'] = celltype_group_fun(sa)
    out = sa.groupby([sa.index, 'SC', 'celltype']).apply(
        lambda x: I.temporal_binning(x,
                                     min_time=evoked_min_time,
                                     max_time=evoked_max_time,
                                     bin_size=evoked_max_time - evoked_min_time,
                                     normalize=False)[1][0])
    out2 = sa.groupby([sa.index,
                       'celltype']).apply(lambda x: I.temporal_binning(
                           x,
                           min_time=ongoing_min_time,
                           max_time=ongoing_max_time,
                           bin_size=ongoing_max_time - ongoing_min_time,
                           normalize=False)[1][0])
    # make sure ongoing activity is normalized to reflect the same timewindow as evoked activity
    out2 = out2 * (float(evoked_max_time) - evoked_min_time) / (
        float(ongoing_max_time) - ongoing_min_time)
    out2.index = [(i[0], 'ongoing', i[1]) for i in out2.index]
    return I.pd.concat([out, out2])


def _fig2C_data_step2(sa,
                      ongoing_min_time=None,
                      ongoing_max_time=None,
                      evoked_min_time=None,
                      evoked_max_time=None,
                      PC=None,
                      SCs=None,
                      client=None,
                      celltype_group_fun=None):
    '''returns the dataframe required for reproducing plot Fig2C.
    Requires a pandas data frame.'''
    ds = [
        _fig2C_data_step1(d,
                          ongoing_min_time=ongoing_min_time,
                          ongoing_max_time=ongoing_max_time,
                          evoked_min_time=evoked_min_time,
                          evoked_max_time=evoked_max_time,
                          PC=PC,
                          SCs=SCs,
                          celltype_group_fun=celltype_group_fun)
        for d in sa.to_delayed()
    ]
    fs = client.compute(ds)
    res = client.gather(fs)
    return I.pd.concat(res)


def get_std_of_active_synapses(df):
    d = df.unstack(0)
    out = d[d.index.get_level_values(0).isin(
        ['PC', 'SC', '2ndSC'])].unstack(-1).sum(axis=0).unstack(0).std(axis=1)
    out.index = [('std_of_total_active_synapses', i) for i in out.index]
    return out


def get_mean_number_of_activations(df):
    return df.unstack(0).mean(axis=1)


def _fig2C_data_step3(df, celltype_renaming_dict=None, combine_L4sp_L4ss=None):
    df = I.pd.concat(
        [get_mean_number_of_activations(df),
         get_std_of_active_synapses(df)]).unstack(0)
    if combine_L4sp_L4ss:
        df.loc['L4sp', :] = df.loc['L4sp', :] + df.loc['L4ss', :]
        df = df.drop('L4ss')
    if celltype_renaming_dict is not None:
        df.index = df.index.map(lambda x: celltype_renaming_dict[x])
    return df


def plot_fig2C_data(df, ax=None):
    if ax is None:
        fig = I.plt.figure()
        ax = fig.add_subplot(111)
    height = 0.5
    names = []
    for lv, name in enumerate(reversed(
            df.index)):  #lv, (name, row) in enumerate(df.iterrows()):
        row = df.loc[name]
        ax.errorbar(row.PC + row.SC + row['2ndSC'],
                    lv,
                    xerr=row.std_of_total_active_synapses,
                    c='k',
                    capsize=3,
                    zorder=0)
        ax.barh(lv, row.PC, height, left=0, color='#888888', edgecolor='k')
        ax.barh(lv, row.SC, height, left=row.PC, color='#BBBBBB', edgecolor='k')
        ax.barh(lv,
                row['2ndSC'],
                height,
                left=row.PC + row.SC,
                color='#FFFFFF',
                edgecolor='k')
        ax.plot([row.ongoing, row.ongoing], [lv - 0.35, lv + 0.35], c='k')
        #ax.barh(lv, 2, 0.7, left = row.ongoing-1, color = '#000000')
        names.append(name)
    ax.set_yticks(list(range(len(names))))
    ax.set_yticklabels(names)
    ax.set_xticks(list(range(0, 1800, 300)))


def fig2C_data(
        sa,
        ongoing_min_time=245 - 25,
        ongoing_max_time=245,
        evoked_min_time=245,
        evoked_max_time=245 + 25,
        PC=['C2', 'S1'],
        SCs=['B1', 'B2', 'B3', 'D1', 'D2', 'D3', 'C1', 'C3'],
        client=None,
        celltype_renaming_dict={
            'L2': 'L2PY',
            'L34': 'L3PY',
            'L4sp': 'L4SP',
            'L4py': 'L4PY',
            'L5st': 'L5IT',
            'L5tt': 'L5PT',
            'L6cc': 'L6cc',
            'L6ccinv': 'L6INV',
            'L6ct': 'L6CT',
            'VPM': 'VPM',
            'INH': 'INH'
        },
        combine_L4sp_L4ss=True,
        fillna=True,
        celltype_group_fun=lambda sa: sa.synapse_type.str.split('_').str[0]):
    data = _fig2C_data_step2(sa,
                             ongoing_min_time=ongoing_min_time,
                             ongoing_max_time=ongoing_max_time,
                             evoked_min_time=evoked_min_time,
                             evoked_max_time=evoked_max_time,
                             PC=PC,
                             SCs=SCs,
                             client=client,
                             celltype_group_fun=celltype_group_fun)
    data = _fig2C_data_step3(data,
                             celltype_renaming_dict=celltype_renaming_dict,
                             combine_L4sp_L4ss=combine_L4sp_L4ss)
    if fillna:
        data = data.fillna(0)
    return data


def plot_fig2C_data(df, ax=None, xticks=list(range(0, 1800, 300))):
    if ax is None:
        fig = I.plt.figure()
        ax = fig.add_subplot(111)
    height = 0.5
    names = []
    for lv, name in enumerate(reversed(
            df.index)):  #lv, (name, row) in enumerate(df.iterrows()):
        row = df.loc[name]
        ax.errorbar(row.PC + row.SC + row['2ndSC'],
                    lv,
                    xerr=row.std_of_total_active_synapses,
                    c='k',
                    capsize=3,
                    zorder=0)
        ax.barh(lv, row.PC, height, left=0, color='#888888', edgecolor='k')
        ax.barh(lv, row.SC, height, left=row.PC, color='#BBBBBB', edgecolor='k')
        ax.barh(lv,
                row['2ndSC'],
                height,
                left=row.PC + row.SC,
                color='#FFFFFF',
                edgecolor='k')
        ax.plot([row.ongoing, row.ongoing], [lv - 0.35, lv + 0.35], c='k')
        #ax.barh(lv, 2, 0.7, left = row.ongoing-1, color = '#000000')
        names.append(name)
    ax.set_yticks(list(range(len(names))))
    ax.set_yticklabels(names)
    if xticks:
        ax.set_xticks(xticks)


@I.dask.delayed
def _fig2C_convert_synfile_to_syn_activation(synfile_path, index=0):
    presyn_cells = []
    with open(synfile_path, 'r') as synfile:
        for line in synfile:
            if not line.startswith('#') and not line.startswith('\n'):
                presyn_cells.append(line.split('\t')[0])

    syn_df = I.pd.DataFrame(index=[index] * len(presyn_cells))
    syn_df['synapse_type'] = presyn_cells
    syn_df[0] = [1.0] * len(presyn_cells)
    return syn_df


def fig2C_convert_synfiles_to_mock_sa(synpathlist):
    '''This is a converter that allows to use the fig2C figure routines,
    which are typically used to display active synapses, to display
    anatomical data from syn files:
    
    In fig2C_data, specify 
               ongoing_min_time = 0,
               ongoing_max_time = 10,
               evoked_min_time = 0,
               evoked_max_time = 10'''

    delayeds = [
        _fig2C_convert_synfile_to_syn_activation(synpath, index=lv)
        for lv, synpath in enumerate(synpathlist)
    ]
    mock_sa_dask_ddf = I.dask.dataframe.from_delayed(delayeds)
    return mock_sa_dask_ddf


# fig2x active synapses by soma distance
def combine_bins(bins_list):
    bins_out = []
    bins_std_out = []
    for i in bins_list[0].index:
        bins_values = I.np.mean([b[i][1] for b in bins_list], axis=0)
        bins_values_std = I.np.std([b[i][1] for b in bins_list], axis=0)
        b = bins_list[0]
        bins_out.append((b[0][0], bins_values))
        bins_std_out.append((b[0][0], bins_values_std))
    return I.pd.Series(bins_out, index = bins_list[0].index), \
                I.pd.Series(bins_std_out, index = bins_list[0].index)


def spatial_synapse_activation_data(
        sa,
        celltype_group_fun=lambda sa: sa.synapse_type.str.split('_').str[0],
        min_time=0,
        max_time=245 + 700,
        spatial_bin_size=50,
        client=None):
    ds = sa.to_delayed(
    )  # this assumes that we have one partition per simulation trial, but if the mdb is optimized, this is not the case

    @I.dask.delayed
    def _helper(sa_pd_all):
        bins_list = []
        for name, sa_pd in sa_pd_all.groupby(sa_pd_all.index):
            bins = sa_pd.groupby(celltype_group_fun(sa_pd))\
                .apply(lambda x: I.spatial_binning(x,
                                                    min_time = min_time,
                                                    max_time = max_time,
                                                    spatial_bin_size = spatial_bin_size))
            bins_list.append(bins)
        return bins_list

    ds = [_helper(d) for d in ds]
    futures = client.compute(ds)
    bins_list = client.gather(futures)
    bins_list = [x for x in bins_list for x in x]
    return combine_bins(bins_list)


def fig2x_active_synapses_by_soma_distance(
        sa,
        min_time=245,
        max_time=245 + 50,
        client=None,
        spatial_bin_size=I.np.arange(0, 1500, 50),
        ax=None,
        colormap=I.color_cellTypeColorMap_L6paper_with_INH):
    if ax is None:
        fig = I.plt.figure(figsize=(10, 5))
        ax = fig.add_subplot(111)

    bins_mean, bins_std = spatial_synapse_activation_data(
        sa,
        min_time=min_time,
        max_time=max_time,
        client=client,
        spatial_bin_size=I.np.arange(0, 1500, 50))

    I.histogram(bins_mean.to_frame(), colormap=colormap, fig=ax)
    I.plt.xlim([min(spatial_bin_size), max(spatial_bin_size)])

    return bins_mean, bins_std


# Panel D
def combine_bins(bins_list):
    bins_out = []
    bins_std_out = []
    for i in bins_list[0].index:
        b = bins_list[0]
        bins_values = I.np.mean([b[i][1] for b in bins_list], axis=0)
        bins_values_std = I.np.std([b[i][1] for b in bins_list], axis=0)
        bins_out.append((b[0][0], bins_values))
        bins_std_out.append((b[0][0], bins_values_std))
    return I.pd.Series(bins_out, index = bins_list[0].index), \
                I.pd.Series(bins_std_out, index = bins_list[0].index)


def temporal_synapse_activation_data(
        sa,
        celltype_group_fun=lambda sa: sa.synapse_type.str.split('_').str[0],
        min_time=0,
        max_time=245 + 700,
        bin_size=1,
        client=None):
    ds = sa.to_delayed()

    @I.dask.delayed
    def _helper(sa_pd):
        bins = sa_pd.groupby(celltype_group_fun(sa_pd))\
            .apply(lambda x: I.temporal_binning(x,
                                                min_time = min_time,
                                                max_time = max_time,
                                                bin_size = bin_size,
                                                normalize = False))
        return bins

    ds = [_helper(d) for d in ds]
    futures = client.compute(ds)
    bins_list = client.gather(futures)
    return combine_bins(bins_list)