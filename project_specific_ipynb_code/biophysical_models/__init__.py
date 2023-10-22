import Interface as I
import pandas as pd
import dask
import matplotlib.pyplot as plt
from biophysics_fitting.hay_evaluation import objectives_BAC, objectives_step
from model_data_base.utils import convertible_to_int

I.sys.path.append('/axon/scratch/abast/project_src/SpikeAnalysis/')


def disable_locking_BE_CAREFUL(client):
    '''Disables locking of model data bases on the client and locally.
    Use to speed up loading data, but only if you can guarantee that there will not be any write access to any database!'''
    client.restart()

    def fun():
        import model_data_base.distributed_lock
        import model_data_base.sqlite_backend.sqlite_backend
        import redis
        model_data_base.distributed_lock.redis = redis
        model_data_base.sqlite_backend.sqlite_backend.locking = False

    client.run(fun)
    fun()


def get_seeds(mdb, max_generations=None):
    '''Returns seeds used for running simulations'''
    seeds = [k for k in list(mdb.keys()) if convertible_to_int(k)]
    if max_generations is not None:
        return sorted([
            s for s in seeds if len(get_generations(mdb[s])) and
            max(get_generations(mdb[s])) == max_generations
        ])
    else:
        return sorted([s for s in seeds if len(get_generations(mdb[s]))])


def get_generations(mdb):
    '''Returns generations stored in mdb'''
    return [
        int(k) for k in list(mdb.keys()) if convertible_to_int(k) and int(k) > 0
    ]


def get_max_objective_from_pdf(pdf, objectives):
    return pdf[objectives].max(axis=1).min()


def augment_model_id(pdf, mdb_id, seed, gen):
    pdf['model_id'] = '_'.join([mdb_id, str(seed), str(gen)])
    pdf['model_id'] = pdf['model_id'] + '_' + pd.Series(pdf.index).astype('str')
    return pdf


def augment_pdf(pdf,
                mdb_id,
                type_,
                morphology,
                seed,
                lv,
                gen,
                additional_columns=[('scale_apical.scale', 'f4'),
                                    ('ephys.SKv3_1.apic.offset', 'f4'),
                                    ('ephys.SKv3_1.apic.slope', 'f4'),
                                    ('hot_zone.outsidescale_sections', 'object')
                                   ],
                objectives=objectives_BAC + objectives_step,
                append={}):
    '''type_: identifier of the optimization, e.g. name of optimization project like CDK_remaining_morphologies_step
    morphology: identifier for the morphology
    seed: seed
    lv: enumerator of the seeds
    gen: generation
    additional_columns: if heterogenous dataframes are expected, additional columns can be specified, which will be filled with NaN if the don't exist.
    Returns: dataframe, augmented with the respective columns'''
    pdf = augment_model_id(pdf, mdb_id, seed, gen)
    pdf['type_'] = type_
    pdf['morphology'] = morphology
    pdf['lv'] = lv
    pdf['seed'] = seed
    pdf['max_'] = pdf[objectives].max(axis=1)
    pdf['gen'] = gen
    for k, dtype in additional_columns:
        if not k in pdf.columns:
            pdf[k] = float('nan')
            pdf[k] = pdf[k].astype(dtype)
    for k in list(append.keys()):
        try:
            len(append[k])
            pdf[k] = [append[k]] * len(pdf)
        except TypeError:
            pdf[k] = append[k]
    return pdf


@dask.delayed
def _helper(m,
            seed,
            lv,
            gen,
            type_,
            morphology,
            additional_columns=[('scale_apical.scale', 'f4'),
                                ('ephys.SKv3_1.apic.offset', 'f4'),
                                ('ephys.SKv3_1.apic.slope', 'f4'),
                                ('hot_zone.outsidescale_sections', 'object')],
            append={},
            objectives=objectives_BAC + objectives_step):
    pdf = m[str(seed)][str(gen)]
    return augment_pdf(pdf,
                       m.get_id(),
                       type_,
                       str(morphology),
                       str(seed),
                       lv,
                       str(gen),
                       additional_columns=additional_columns,
                       append=append,
                       objectives=objectives)


def get_model_ddf_from_mdb(m,
                           type_='unspecified',
                           morphology='unspecified',
                           return_delayeds=False,
                           add_fixed_params=True,
                           objectives=objectives_BAC + objectives_step):
    delayeds = []
    if add_fixed_params:
        fixed_params = m['get_fixed_params'](m)
    else:
        fixed_params = {}
    for lv, seed in enumerate(get_seeds(m)):
        for gen in get_generations(m[seed]):
            delayeds.append(
                _helper(m,
                        seed,
                        lv,
                        gen,
                        type_,
                        morphology,
                        append=fixed_params,
                        objectives=objectives))
    if return_delayeds:
        return delayeds
    else:
        return dask.dataframe.from_delayed(delayeds)


def get_model_ddf_from_encapsulating_mdb(mdbs,
                                         morphologies=None,
                                         type_='unspecified',
                                         add_fixed_params=True,
                                         objectives=objectives_BAC +
                                         objectives_step,
                                         return_delayeds=False):
    delayeds = []
    if morphologies is None:
        morphologies = list(mdbs.keys())
    for morphology in morphologies:
        m = mdbs[morphology]
        delayeds.extend(
            get_model_ddf_from_mdb(m,
                                   morphology=morphology,
                                   return_delayeds=True,
                                   add_fixed_params=add_fixed_params,
                                   objectives=objectives))
    if return_delayeds:
        return delayeds
    else:
        return dask.dataframe.from_delayed(delayeds)


def get_ddf_selected(ddf,
                     BAC_limit=3.5,
                     step_limit=4.5,
                     objectives_BAC=objectives_BAC,
                     objectives_step=objectives_step,
                     compute_and_sort=False):

    objectives = objectives_BAC + objectives_step
    ddf['sort_column'] = ddf[objectives].max(axis=1)
    if len(objectives_step) == 0:
        ddf = ddf[ddf[objectives_BAC].max(axis=1) < BAC_limit]
    else:
        ddf = ddf[(ddf[objectives_step].max(axis=1) < step_limit) &
                  (ddf[objectives_BAC].max(axis=1) < BAC_limit)]
    return ddf


##########
# params plot

params_order = [
    'ephys.NaTa_t.soma.gNaTa_tbar', 'ephys.Nap_Et2.soma.gNap_Et2bar',
    'ephys.K_Pst.soma.gK_Pstbar', 'ephys.K_Tst.soma.gK_Tstbar',
    'ephys.SK_E2.soma.gSK_E2bar', 'ephys.SKv3_1.soma.gSKv3_1bar',
    'ephys.Ca_HVA.soma.gCa_HVAbar', 'ephys.Ca_LVAst.soma.gCa_LVAstbar',
    'ephys.CaDynamics_E2.soma.gamma', 'ephys.CaDynamics_E2.soma.decay',
    'ephys.none.soma.g_pas', 'ephys.none.axon.g_pas', 'ephys.none.dend.g_pas',
    'ephys.none.apic.g_pas', 'ephys.NaTa_t.axon.gNaTa_tbar',
    'ephys.Nap_Et2.axon.gNap_Et2bar', 'ephys.K_Pst.axon.gK_Pstbar',
    'ephys.K_Tst.axon.gK_Tstbar', 'ephys.SK_E2.axon.gSK_E2bar',
    'ephys.SKv3_1.axon.gSKv3_1bar', 'ephys.Ca_HVA.axon.gCa_HVAbar',
    'ephys.Ca_LVAst.axon.gCa_LVAstbar', 'ephys.CaDynamics_E2.axon.gamma',
    'ephys.CaDynamics_E2.axon.decay', 'ephys.Im.apic.gImbar',
    'ephys.NaTa_t.apic.gNaTa_tbar', 'ephys.SKv3_1.apic.gSKv3_1bar',
    'ephys.Ca_HVA.apic.gCa_HVAbar', 'ephys.Ca_LVAst.apic.gCa_LVAstbar',
    'ephys.SK_E2.apic.gSK_E2bar', 'ephys.CaDynamics_E2.apic.gamma',
    'ephys.CaDynamics_E2.apic.decay', 'ephys.SKv3_1.apic.offset',
    'ephys.SKv3_1.apic.slope', 'scale_apical.scale'
]

params_name_mapping = {
    'ephys.NaTa_t.soma.gNaTa_tbar': 's.Na_t',
    'ephys.Nap_Et2.soma.gNap_Et2bar': 's.Na_p',
    'ephys.K_Pst.soma.gK_Pstbar': 's.K_p',
    'ephys.K_Tst.soma.gK_Tstbar': 's.K_t',
    'ephys.SK_E2.soma.gSK_E2bar': 's.SK',
    'ephys.SKv3_1.soma.gSKv3_1bar': 's.Kv_3.1',
    'ephys.Ca_HVA.soma.gCa_HVAbar': 's.Ca_H',
    'ephys.Ca_LVAst.soma.gCa_LVAstbar': 's.Ca_L',
    'ephys.CaDynamics_E2.soma.gamma': 's.Y',
    'ephys.CaDynamics_E2.soma.decay': 's.T_decay',
    'ephys.none.soma.g_pas': 's.leak',
    'ephys.none.axon.g_pas': 'ax.leak',
    'ephys.none.dend.g_pas': 'b.leak',
    'ephys.none.apic.g_pas': 'a.leak',
    'ephys.NaTa_t.axon.gNaTa_tbar': 'ax.Na_t',
    'ephys.Nap_Et2.axon.gNap_Et2bar': 'ax.Na_p',
    'ephys.K_Pst.axon.gK_Pstbar': 'ax.K_p',
    'ephys.K_Tst.axon.gK_Tstbar': 'ax.K_t',
    'ephys.SK_E2.axon.gSK_E2bar': 'ax.SK',
    'ephys.SKv3_1.axon.gSKv3_1bar': 'ax.Kv_3.1',
    'ephys.Ca_HVA.axon.gCa_HVAbar': 'ax.Ca_H',
    'ephys.Ca_LVAst.axon.gCa_LVAstbar': 'ax.Ca_L',
    'ephys.CaDynamics_E2.axon.gamma': 'ax.Y',
    'ephys.CaDynamics_E2.axon.decay': 'ax.T_decay',
    'ephys.Im.apic.gImbar': 'a.I_m',
    'ephys.NaTa_t.apic.gNaTa_tbar': 'a.Na_t',
    'ephys.SKv3_1.apic.gSKv3_1bar': 'a.Kv_3.1',
    'ephys.Ca_HVA.apic.gCa_HVAbar': 'a.Ca_H',
    'ephys.Ca_LVAst.apic.gCa_LVAstbar': 'a.Ca_L',
    'ephys.SK_E2.apic.gSK_E2bar': 'a.SK',
    'ephys.CaDynamics_E2.apic.gamma': 'a.Y',
    'ephys.CaDynamics_E2.apic.decay': 'a.T_decay',
    'ephys.SKv3_1.apic.offset': 'a.Kv_3.1_offset',
    'ephys.SKv3_1.apic.slope': 'a.Kv_3.1_slope',
    'scale_apical.scale': 'a.scale'
}


def get_param_boundaries():
    from biophysics_fitting.hay_complete_default_setup import get_hay_params_pdf
    pdf = get_hay_params_pdf()
    pdf = pdf.append(
        pd.DataFrame({
            'SKv3_1.apic.offset': {
                'min': 0,
                'max': 1
            },
            'SKv3_1.apic.slope': {
                'min': -3,
                'max': 0
            }
        }).T)
    pdf.index = pdf.index.map(lambda x: 'ephys.' + x)
    pdf = pdf.append(
        pd.DataFrame({
            'scale_apical.scale': {
                'min': 0,
                'max': 3
            }
        }).T)
    return pdf


def normalize_params(params_df,
                     normalize_range=True,
                     normalize_naming=True,
                     params_order=params_order,
                     params_name_mapping=params_name_mapping):
    boundaries = get_param_boundaries()
    params_df = params_df[boundaries.index]
    if normalize_range:
        params_df = params_df.apply(
            lambda x: (x - boundaries.loc[x.name]['min']) /
            (boundaries.loc[x.name]['max'] - boundaries.loc[x.name]['min']))

    params_df = params_df[params_order]

    if normalize_naming:
        params_df.columns = params_df.columns.map(
            lambda x: params_name_mapping[x])
    return params_df


def min_max_plot(pdf,
                 ax=None,
                 color_marker_map=None,
                 plot_individual_ticks=True,
                 offset=0,
                 color_of_stick='k'):
    color = dict(boxes='black', whiskers='black', medians='white', caps='black')
    if ax is None:
        fig = plt.figure(figsize=(10, 4), dpi=200)
        ax = fig.add_subplot(111)
    for lv, c in enumerate(pdf.columns):
        s = pdf[c]
        d = .2
        plt.plot([lv + offset, lv + offset], [s.min(), s.max()],
                 c=color_of_stick)
        if plot_individual_ticks:
            import six
            for i, x in six.iteritems(s):
                if color_marker_map is None:
                    color = 'k'
                    marker = '_'
                else:
                    color, marker = color_marker_map[i]
                if marker is not None:
                    ax.scatter(lv, x, c=color, marker=marker, zorder=10)
    ax.set_xticks(list(range(len(pdf.columns))))
    _ = ax.set_xticklabels(pdf.columns, rotation=90)


########
# radii plot
########
from project_specific_ipynb_code.hot_zone import get_cell_object_from_hoc, Dendrogram


def radii_plot(cell, ax=None):
    if ax is None:
        fig = I.plt.figure(figsize=(15, 3))
        ax = fig.add_subplot(111)
    d = Dendrogram(cell)
    for sec in cell.sections:
        s_ = d.get_db_by_sec(sec)
        xs = I.np.array(sec.relPts) * sec.L + s_['x_dist_start']
        ys = sec.diamList
        if sec.label == 'Dendrite':
            c = 'k'
        elif sec.label == 'ApicalDendrite':
            c = 'r'
        else:
            c = 'grey'
        I.plt.plot(xs, ys, c=c, linewidth=.5)


def plot_cell(cell, ax=None, offset=[0, 0, 0]):
    import numpy as np
    from matplotlib.collections import LineCollection
    import matplotlib.pyplot as plt
    cs = []
    xs = []
    ys = []
    diams = []
    secs = cell.sections
    for sec in secs:
        if sec.label in ('AIS', 'Myelin'):
            continue
        # c = [get_closest_seg(sec,x).SKv3_1.gSKv3_1bar for x in sec.relPts]
        c = [get_closest_seg(sec, x).Ih.gIhbar for x in sec.relPts]
        diam = [get_closest_seg(sec, x).diam for x in sec.relPts]
        x, y = [pt[1] - offset[1] for pt in sec.pts
               ], [pt[2] - offset[2] for pt in sec.pts]
        cs.extend(c)
        xs.extend(x)
        ys.extend(y)
        diams.extend(diam)
        a.plot(x, y, c='k', linewidth=.1)
        xx = I.np.array(x)
        yy = I.np.array(y)
        llwidths = I.np.array(diam)
        points = I.np.array([xx, yy]).T.reshape(-1, 1, 2)
        segments = I.np.concatenate([points[:-1], points[1:]], axis=1)
        lc = LineCollection(segments, linewidths=llwidths[:-1] * 0.5, color='k')
        a.add_collection(lc)
    I.plt.gca().set_aspect('equal')


def compute_soma_distance_radius_dict_of_trunk(cell):
    sec = get_main_bifurcation_section(cell)
    out_diams = []
    out_lens = []
    out_Ls = []
    while True:
        out_diams.append(sec.diamList)
        out_lens.append(I.np.array(sec.relPts) * sec.L)
        out_Ls.append(sec.L)
        sec = sec.parent
        if sec.label == 'Soma':
            break
    out_diams, out_lens, out_Ls = out_diams[::-1], out_lens[::-1], out_Ls[::-1]
    out_Ls = I.np.cumsum([0] + out_Ls[:-1])
    out_lens_absolute = [
        l + out_Ls[lv] for lv, llist in enumerate(out_lens) for l in llist
    ]
    out_diams = [x for x in out_diams for x in x]
    return out_lens_absolute, out_diams


###########
# refractory period
###########
import spike_analysis.core


def plot_vt(voltage_traces, key='BAC.hay_measure'):
    I.plt.figure()
    I.plt.plot(voltage_traces[key]['tVec'],
               voltage_traces[key]['vList'][0],
               c='k')
    try:
        I.plt.plot(voltage_traces[key]['tVec'],
                   voltage_traces[key]['vList'][1],
                   c='r')
    except IndexError:
        pass
    I.display.display(I.plt.gcf())
    I.plt.close()


@I.cache
def _helper_get_simulator(m):
    from copy import deepcopy
    return deepcopy(m['get_Simulator'](m))


def get_refractory_period_simrun(m, params, delay=None, soma_or_apical='soma'):
    try:
        m.basedir
    except:
        simulator = m
    else:
        simulator = _helper_get_simulator(m)
    simulator.setup.stim_setup_funs = [
        x for x in simulator.setup.stim_setup_funs if 'BAC' in x[0]
    ]
    simulator.setup.stim_run_funs = [
        x for x in simulator.setup.stim_run_funs if 'BAC' in x[0]
    ]
    simulator.setup.stim_response_measure_funs = [
        x for x in simulator.setup.stim_response_measure_funs if 'BAC' in x[0]
    ]
    params_selected = params.copy()
    params_selected['BAC.stim.delay'] = [295, 295 + delay]
    params_selected['BAC.run.tStop'] = 295 + delay + 400
    with I.silence_stdout:
        voltage_traces = simulator.run(params_selected)
    if soma_or_apical == 'soma':
        t, v = voltage_traces['BAC.hay_measure']['tVec'], voltage_traces[
            'BAC.hay_measure']['vList'][0]
        n = len(I.sca.simple_spike_detection(t, v))

    elif soma_or_apical == 'apical':
        t, v = voltage_traces['BAC.hay_measure']['tVec'], voltage_traces[
            'BAC.hay_measure']['vList'][1]
        spike_times = I.sca.simple_spike_detection(t, v, threshold=-20)
        spike_times = spike_analysis.core.filter_short_ISIs(spike_times, 35)
        n = len(spike_times)

        #t, v = voltage_traces['BAC.hay_measure']['tVec'], voltage_traces['BAC.hay_measure']['vList'][1]
        #reader = spike_analysis.core.ReaderDummy(t,v)
        #sdct = spike_analysis.core.SpikeDetectionCreastTrough(reader, lim_creast = -20., lim_trough = -60.,
        #                                       max_creast_trough_interval = 50., tdelta = 10.)
        #sdct.run_analysis()
        #n = len(sdct.spike_times)

    return voltage_traces, n


def get_refractory_period(m,
                          params,
                          soma_or_apical='soma',
                          delay=2000,
                          n_threashold=6,
                          accuracy=10,
                          verbose=False):
    _run_helper = I.partial(get_refractory_period_simrun,
                            m,
                            params,
                            soma_or_apical=soma_or_apical)
    vt, n = _run_helper(delay=delay)
    if not n >= n_threashold:
        return -1
    delay_upper = delay
    delay_lower = 0
    while delay_upper - delay_lower >= accuracy:
        current_delay = (delay_upper + delay_lower) / 2.
        if verbose:
            print('checking for delay ', current_delay)
        vt, n = _run_helper(delay=current_delay)
        if n >= n_threashold:
            delay_upper = current_delay
            if verbose:
                print('reducing upper delay to ', delay_upper)
        else:
            delay_lower = current_delay
            if verbose:
                print('increasing lower delay to ', delay_lower)
    return delay_lower, delay_upper, delay_lower * 0.5 + delay_upper * 0.5


def get_refractory_period_analysis(m, params, accuracy=10):
    return {
        '2_Ca_spikes':
            get_refractory_period(m,
                                  params,
                                  soma_or_apical='apical',
                                  n_threashold=2,
                                  accuracy=accuracy),
        '6_Na_spikes':
            get_refractory_period(m,
                                  params,
                                  soma_or_apical='soma',
                                  n_threashold=6,
                                  accuracy=accuracy),
        '5_Na_spikes':
            get_refractory_period(m,
                                  params,
                                  soma_or_apical='soma',
                                  n_threashold=5,
                                  accuracy=accuracy),
        '4_Na_spikes':
            get_refractory_period(m,
                                  params,
                                  soma_or_apical='soma',
                                  n_threashold=4,
                                  accuracy=accuracy)
    }


####################################
# current analysis
####################################

I.sys.path.append('/axon/scratch/abast/project_src/SpikeAnalysis/')
import project_specific_ipynb_code.hot_zone

rangeVarsApical = [
    'NaTa_t.ina', 'Ca_HVA.ica', 'Ca_LVAst.ica', 'SKv3_1.ik', 'SK_E2.ik',
    'Ih.ihcn', 'Im.ik'
]
rangeVarsAllChannels = rangeVarsApical + ['Nap_Et2.ina', 'K_Pst.ik', 'K_Tst.ik']


def get_cell(s,
             p,
             pdf_best_run_selected=None,
             range_vars=rangeVarsApical +
             ['Nap_Et2.ina', 'K_Pst.ik', 'K_Tst.ik']):
    with I.silence_stdout:
        cell, p = s.get_simulated_cell(p[params_list], 'BAC')
    if range_vars:
        for rv in rangeVarsApical + ['Nap_Et2.ina', 'K_Pst.ik', 'K_Tst.ik']:
            cell.record_range_var(rv)
        I.scp.init_neuron_run(I.scp.NTParameterSet({
            'tStop': 600,
            'dt': 0.025,
            'T': 34,
            'Vinit': -75
        }),
                              vardt=True)
    return cell


class CurrentAnalysis:

    def __init__(self,
                 cell_or_dict=None,
                 secID='bifurcation',
                 segID=-1,
                 rangeVars=None,
                 colormap=None,
                 tVec=None):
        # set attributes
        if not isinstance(cell_or_dict, dict):
            self.mode = 'cell'
            self.cell = cell = cell_or_dict
            self.t = cell.tVec
            if secID == 'bifurcation':
                sec = project_specific_ipynb_code.hot_zone.get_main_bifurcation_section(
                    cell)
            else:
                sec = cell.sections[secID]
            self.sec = sec
            self.secID = cell.sections.index(sec)
            self.segID = segID
            self.seg = [seg for seg in sec][segID]
            if rangeVars is None:
                self.rangeVars = cell.soma.recordVars.keys()
            else:
                self.rangeVars = rangeVars
        else:
            self.mode = 'dict'
            self.t = tVec
            self.rangeVars = rangeVars
            self.cell = cell_or_dict
            self.sec = None
        self.colormap = colormap
        # compute currents
        self._compute_current_arrays()

    def _get_current_by_rv(self, rv):
        try:
            if self.mode == 'dict':
                return self.cell[rv]
            elif self.mode == 'cell':
                return I.np.array(self.sec.recordVars[rv][self.segID])
            else:
                raise ValueError()
        except (KeyError, IndexError):
            return I.np.array([float('nan')] * len(self.t))

    def _compute_current_arrays(self):
        out_depolarizing = []
        out_hyperpolarizing = []
        for rv in self.rangeVars:
            x = self._get_current_by_rv(rv)
            out_depolarizing.append(I.np.where(x >= 0, 0, x))
            out_hyperpolarizing.append(I.np.where(x < 0, 0, x))
        self.depolarizing_currents = I.np.array(out_depolarizing) * -1
        self.hyperpolarizing_currents = I.np.array(out_hyperpolarizing) * -1
        self.depolarizing_currents_sum = self.depolarizing_currents.sum(axis=0)
        self.hyperpolarizing_currents_sum = self.hyperpolarizing_currents.sum(
            axis=0)
        self.net_current = self.depolarizing_currents_sum + self.hyperpolarizing_currents_sum
        self.depolarizing_currents_normalized = self.depolarizing_currents / self.depolarizing_currents_sum
        self.hyperpolarizing_currents_normalized = self.hyperpolarizing_currents / self.hyperpolarizing_currents_sum * -1
        if self.mode == 'cell':
            self.voltage_trace = self.sec.recVList[self.segID]
        else:
            self.voltage_trace = None

    def plot_areas(self,
                   ax=None,
                   normalized=False,
                   plot_net=False,
                   plot_voltage=False,
                   t_stim=295,
                   select_window_relative_to_stim=(0, 55)):
        t = I.np.array(self.t) - t_stim
        if ax is None:
            fig = I.plt.figure(figsize=(10, 4), dpi=200)
            ax = fig.add_subplot(111)

        def __helper(currents, plot_label=True):
            dummy = I.np.cumsum(currents, axis=0)
            dummy = I.np.vstack([I.np.zeros(dummy.shape[1]), dummy])
            for lv, rv in enumerate(self.rangeVars):
                x, y1, y2 = t, dummy[lv, :], dummy[lv + 1, :]
                select = (x >= select_window_relative_to_stim[0]) & (
                    x <= select_window_relative_to_stim[1])
                x, y1, y2 = x[select], y1[select], y2[select]
                ax.fill_between(x,
                                -y1,
                                -y2,
                                label=rv if plot_label else None,
                                color=self.colormap[rv],
                                linewidth=0)

        if normalized:
            __helper(self.depolarizing_currents_normalized)
            __helper(self.hyperpolarizing_currents_normalized, False)
            ax.plot(t, self.depolarizing_currents_sum + 1, c='k')
            ax.plot(t, self.hyperpolarizing_currents_sum - 1, c='k')
        else:
            __helper(self.depolarizing_currents)
            __helper(self.hyperpolarizing_currents, False)
        if plot_net:
            ax.plot(t, self.net_current, 'k', label='net current')
        if plot_voltage:
            ax2 = ax.twinx()
            select = (t >= select_window_relative_to_stim[0]) & (
                t <= select_window_relative_to_stim[1])
            x, y = t[select], I.np.array(self.cell.soma.recVList[0])[select]
            ax2.plot(x, y, 'k')
            x, y = t[select], I.np.array(self.voltage_trace)[select]
            ax2.plot(x, y, c='#f9b233')

    def plot_lines(self, ax=None, legend=True):
        if ax is None:
            fig = I.plt.figure(figsize=(15, 6))
            ax = fig.add_subplot(111)
        for lv, name in enumerate(self.rangeVars):
            ax.plot(self.t,
                    I.np.array(self.sec.recordVars[name][self.segID]) * -1,
                    label=name)


def unfold_dict(d):
    out = {}
    for k, v in six.iteritems(d):
        if not isinstance(v, dict):
            out[k] = v
        else:
            for kk, vv in six.iteritems(v):
                out[k + '.' + kk] = vv
    return out


def get_values_at_timepoint(tVec, value_dict, t):
    range_vars = [
        'SK_E2.ik', 'Im.ik', 'Ca_LVAst.ica', 'SKv3_1.ik', 'Ca_HVA.ica',
        'Ih.ihcn', 'NaTa_t.ina'
    ]
    i = I.np.argmin(I.np.abs(tVec - t))
    return {k: v[i] for k, v in six.iteritems(value_dict) if k in range_vars}


colormap = {
    'NaTa_t.ina': 'red',
    'Ca_HVA.ica': 'dodgerblue',
    'Ca_LVAst.ica': 'lightblue',
    'SKv3_1.ik': 'lightgreen',
    'SK_E2.ik': 'darkgreen',
    'Ih.ihcn': 'grey',
    'Im.ik': 'yellow'
}


def get_charge(ca, tmin=295, tmax=350):
    t = I.np.arange(0, tmax, 0.025)
    v = I.np.interp(t, ca.t, ca.depolarizing_currents_sum)  # [select]
    select = (t > tmin) & (t < tmax)
    v2 = I.np.interp(t, ca.t, ca.hyperpolarizing_currents_sum)  # [select]
    return I.np.abs(v[select]).sum() * 0.025 + I.np.abs(
        v2[select]).sum() * 0.025


def get_charges(ca, tmin=295, tmax=350):
    t = I.np.arange(0, tmax, 0.025)
    v = ca.depolarizing_currents + ca.hyperpolarizing_currents
    vs = {k: v[lv, :] for lv, k in enumerate(ca.rangeVars)}
    vs = {k: I.np.abs(I.np.interp(t, ca.t, v)) for k, v in six.iteritems(vs)}
    select = (t > tmin) & (t < tmax)
    vs = {k: v[select].sum() * 0.025 for k, v in six.iteritems(vs)}
    return vs


def evaluate_currents(voltage_traces_dict):
    vt = voltage_traces_dict
    range_vars = [
        'SK_E2.ik', 'Im.ik', 'Ca_LVAst.ica', 'SKv3_1.ik', 'Ca_HVA.ica',
        'Ih.ihcn', 'NaTa_t.ina'
    ]
    out_ = {}
    keys = vt['bAP.range_vars'].keys(
    )  # recording sites, also includes proximal and distal site
    # rename proximal and distal site, which is indicated by the numerical value of its soma distance to 'prox' and 'dist'
    min_ = min([k for k in keys if I.utils.convertible_to_int(k)])
    max_ = max([k for k in keys if I.utils.convertible_to_int(k)])
    dict_ = {
        min_: 'prox',
        max_: 'dist',
        'bifurcation': 'bifurcation',
        'Soma': 'Soma',
        'AIS': 'AIS'
    }
    keys_new = [dict_[k] for k in keys]
    # update names in dictionary accordingly
    vt_new = {
        kk: {
            kn: vt[kk][k] for kn, k in zip(keys_new, keys)
        } for kk in ['bAP.range_vars', 'BAC.range_vars']
    }
    # save densities of mechanisms at respective location
    out_['constants_bifurcation'] = vt_new['BAC.range_vars']['bifurcation'][
        'constants'].item()
    out_['constants_prox'] = vt_new['BAC.range_vars']['prox']['constants'].item(
    )
    out_['constants_dist'] = vt_new['BAC.range_vars']['dist']['constants'].item(
    )
    # save currents at respective location
    for stim in ['bAP.range_vars', 'BAC.range_vars']:
        prefix = stim.split('.')[0]
        tVec = vt[prefix + '.' + 'hay_measure']['tVec']
        for k in keys_new:
            out_[prefix + '_' + k + '_current_550ms'] = get_values_at_timepoint(
                tVec, vt_new[stim][k], 490)
            out_[prefix + '_' + k + '_current_250ms'] = get_values_at_timepoint(
                tVec, vt_new[stim][k], 250)
            ca = CurrentAnalysis(vt_new[stim][k],
                                 tVec=tVec,
                                 rangeVars=range_vars,
                                 colormap=colormap)
            out_[prefix + '_' + k + '_charges'] = get_charges(ca)
            out_[prefix + '_' + k + '_charge'] = get_charge(ca)
    return unfold_dict(out_)


######################################
# change simulator to additionally report apical dendrite currents
######################################
from biophysics_fitting.utils import _get_apical_sec_and_i_at_distance


def _init_range_var_recording_in_segment(seg, var_list, mech=None):
    import neuron
    out = {}
    for var in var_list:
        if '.' in var:
            mech, var_ = var.split('.')
            hRef = eval('seg.' + mech + '._ref_' + var_)
        else:
            mech = None
            hRef = eval('seg._ref_' + var)
        vec = neuron.h.Vector()
        vec.record(hRef)
        out[var] = vec
    return out


def fun_setup_current_recording(cell, params=None):
    distance = params['distances']
    seg_soma = [seg for seg in cell.soma][0]
    seg_AIS = [sec for sec in cell.sections if sec.label == 'AIS'][0]
    seg_AIS = [seg for seg in seg_AIS][0]
    segs = [seg_AIS, seg_soma]
    for d in distance:
        if I.utils.convertible_to_int(d):
            sec, mindx, minSeg = _get_apical_sec_and_i_at_distance(cell, d)
            seg = [seg for seg in sec][minSeg]
        elif d == 'bifurcation':
            sec = project_specific_ipynb_code.hot_zone.get_main_bifurcation_section(
                cell)
            seg = [seg for seg in sec][-1]
        segs.append(seg)
    distance = ['Soma', 'AIS'] + list(distance)
    range_vars = [
        'NaTa_t.ina', 'Ca_LVAst.ica', 'Ca_HVA.ica', 'Ih.ihcn', 'Im.ik',
        'SKv3_1.ik', 'SK_E2.ik', 'ik', 'ina', 'ica', 'cai', 'eca', 'v'
    ]
    constants = [
        'NaTa_t.gNaTa_tbar', 'Ca_LVAst.gCa_LVAstbar', 'Ca_HVA.gCa_HVAbar',
        'Ih.gIhbar', 'Im.gImbar', 'SKv3_1.gSKv3_1bar', 'SK_E2.gSK_E2bar', 'ek',
        'ena'
    ]
    range_vars_soma = ['Nap_Et2.ina', 'K_Pst.ik', 'K_Tst.ik'] + [
        'NaTa_t.ina', 'Ca_LVAst.ica', 'Ca_HVA.ica', 'Ih.ihcn', 'SKv3_1.ik',
        'SK_E2.ik', 'ik', 'ina', 'ica', 'cai', 'eca', 'v'
    ]
    constants_soma = [
        'Nap_Et2.gNap_Et2bar', 'K_Pst.gK_Pstbar', 'K_Tst.gK_Tstbar'
    ] + [
        'NaTa_t.gNaTa_tbar', 'Ca_LVAst.gCa_LVAstbar', 'Ca_HVA.gCa_HVAbar',
        'Ih.gIhbar', 'SKv3_1.gSKv3_1bar', 'SK_E2.gSK_E2bar', 'ek', 'ena'
    ]
    cell.range_vars_dict = {}
    assert len(distance) == len(segs)
    for d, seg in zip(distance, segs):
        if not d in ('Soma', 'AIS'):
            range_vars_dict = _init_range_var_recording_in_segment(
                seg, range_vars)
            dict_ = {}
            for c in constants:  # dict comprehension does not work as eval doesn't know the seg reference then
                dict_[c] = eval('seg.' + c)
            range_vars_dict['constants'] = dict_
        else:
            range_vars_dict = _init_range_var_recording_in_segment(
                seg, range_vars_soma)
            dict_ = {}
            for c in constants_soma:  # dict comprehension does not work as eval doesn't know the seg reference then
                dict_[c] = eval('seg.' + c)
            range_vars_dict['constants'] = dict_
        cell.range_vars_dict[d] = range_vars_dict
    return cell


def _param_modify_function_put_recording_sites_for_range_var_recording(params):
    if not I.utils.convertible_to_int(params['bAP.hay_measure.recSite1']):
        raise
    distances = [
        float(params['bAP.hay_measure.recSite1']),
        float(params['bAP.hay_measure.recSite2']), 'bifurcation'
    ]
    params['record_range_vars.distances'] = distances
    return params


import six


def return_recorded_range_vars(cell, params=None):
    return {
        kk: {
            k: I.np.array(v) for k, v in six.iteritems(range_vars_dict)
        } for kk, range_vars_dict in six.iteritems(cell.range_vars_dict)
    }


def modify_simulator_to_record_apical_dendrite_conductances(simulator):
    s = simulator
    if not 'range_vars_params' in [k[0] for k in s.setup.params_modify_funs]:
        s.setup.params_modify_funs.append([
            'range_vars_params',
            _param_modify_function_put_recording_sites_for_range_var_recording
        ])
        s.setup.cell_modify_funs.append(
            ['record_range_vars', fun_setup_current_recording])
        keys = [k[0] for k in s.setup.stim_response_measure_funs]
        for k in keys:
            print(k)
            prefix = k.split('.')[0]
            s.setup.stim_response_measure_funs.append(
                [prefix + '.range_vars', return_recorded_range_vars])
    return s


def modify_simulator_to_not_run_step(simulator):

    def delete_step_stuff_from_list(l):
        return [k for k in l if not 'step' in k[0].lower()]

    s = simulator
    s.setup.stim_response_measure_funs = delete_step_stuff_from_list(
        s.setup.stim_response_measure_funs)
    s.setup.stim_run_funs = delete_step_stuff_from_list(s.setup.stim_run_funs)
    s.setup.stim_setup_funs = delete_step_stuff_from_list(
        s.setup.stim_setup_funs)
    return s


######################################


def boxplot(data, x, ax, c='k'):
    ax.boxplot(data,
               positions=[x],
               patch_artist=True,
               boxprops=dict(facecolor=c, color=c),
               capprops=dict(color=c),
               whiskerprops=dict(color=c),
               flierprops=dict(color=c, markeredgecolor=c),
               medianprops=dict(color='white'),
               whis=[0, 100])


#####################################


def interpolate_voltage_trace(voltage_trace_):
    t = voltage_trace_['tVec']
    t_new = I.np.arange(0, max(t), 0.025)
    vList_new = [I.np.interp(t_new, t, v) for v in voltage_trace_['vList']
                ]  # I.np.interp
    return {'tVec': t_new, 'vList': vList_new}


import six


def interpolate_voltage_traces(voltage_traces_):
    return {
        k: interpolate_voltage_trace(v)
        for k, v in six.iteritems(voltage_traces_)
    }


###################################


def visualize_vt(vt, fig=None, soma_color='k', dend_color='#f7941d'):
    plt = I.plt
    if fig is None:
        fig = plt.figure(dpi=200, figsize=(8, 6))
    ax = fig.add_subplot(2, 2, 1)
    t = vt['BAC.hay_measure']['tVec']
    vs = vt['BAC.hay_measure']['vList']
    select = (t >= 295 - 10) & (t < 295 + 80)
    ax.plot(t[select] - 295, vs[0][select], soma_color)
    # ax.plot(t[select]-295,vs[2][select], '#f7941d')
    ax.plot(t[select] - 295, vs[1][select], dend_color)
    ax.plot([20, 40], [30, 30])
    ax.plot([50, 50], [30, 10])

    ax = fig.add_subplot(2, 2, 2)
    t = vt['bAP.hay_measure']['tVec']
    vs = vt['bAP.hay_measure']['vList']
    select = (t >= 295 - 10) & (t < 295 + 80)
    ax.plot(t[select] - 295, vs[0][select], soma_color)
    ax.plot(t[select] - 295, vs[2][select], dend_color)
    ax.plot([20, 40], [30, 30])
    ax.plot([50, 50], [30, 10])

    ax = fig.add_subplot(2, 3, 4)
    t = vt['StepOne.hay_measure']['tVec']
    vs = vt['StepOne.hay_measure']['vList']
    select = (t >= 600) & (t < 2800)
    ax.plot(t[select] - 700, vs[0][select], soma_color)
    ax.plot([500, 1500], [30, 30])
    ax.plot([2050, 2050], [30, 10])

    ax = fig.add_subplot(2, 3, 5)
    t = vt['StepTwo.hay_measure']['tVec']
    vs = vt['StepTwo.hay_measure']['vList']
    select = (t >= 600) & (t < 2800)
    ax.plot(t[select] - 700, vs[0][select], soma_color)
    ax.plot([500, 1500], [30, 30])
    ax.plot([2050, 2050], [30, 10])

    ax = fig.add_subplot(2, 3, 6)
    t = vt['StepThree.hay_measure']['tVec']
    vs = vt['StepThree.hay_measure']['vList']
    select = (t >= 600) & (t < 2800)
    ax.plot(t[select] - 700, vs[0][select], soma_color)
    ax.plot([500, 1500], [30, 30])
    ax.plot([2050, 2050], [30, 10])

    for ax in fig.axes:
        ax.set_ylim(-90, 40)
        ax.axis('off')