import Interface as I


def read_smr_file(path):
    # copying file to tmp_folder to avoid modifying it at all cost
    import neo
    dest_folder = I.tempfile.mkdtemp()
    I.shutil.copy(path, dest_folder)
    path = I.os.path.join(dest_folder, I.os.path.basename(path))
    reader = neo.io.Spike2IO(filename=path)
    data = reader.read(lazy=False)[0]
    I.shutil.rmtree(dest_folder)
    return data


import six


def get_period_label_by_time(periods, t):
    for k, (tmin, tmax) in six.iteritems(periods):
        if tmin <= t < tmax:
            return k
    return 'undefined'


def get_st_from_spike_times_and_stim_times(name, spike_times, stim_times):
    stim_interval = _find_stimulus_interval(stim_times)
    out = []
    for lv, stim_time in enumerate(stim_times):
        values = [
            s - stim_time
            for s in spike_times
            if ((s - stim_time) >= 0) and ((s - stim_time) < stim_interval)
        ]
        values = I.pd.Series({lv: v for lv, v in enumerate(values)})
        values.name = name + '/' + str(lv)
        out.append(values)
    out = I.pd.DataFrame(out)
    return out


# get_st_from_spike_times_and_stim_times('test', [10,22,34,56,67,8, 9], range(0,100,10))

## original spike detection code
# def get_peaks_above(t, v, lim, tdelta = 0):
#     assert len(t) == len(v)
#     out_t = []
#     out_v = []
#     for lv in range(1, len(t) - 1):
#         if (v[lv] > v[lv - 1]) and (v[lv] > v[lv + 1]):
#             if v[lv] > lim:
#                 if out_t:
#                     if t[lv] - out_t[-1] < tdelta:
#                         continue
#                 out_t.append(t[lv])
#                 out_v.append(v[lv])
#
#     return out_t, out_v
# get_peaks_above([0,1,2,3,4,5,6,7,8], [0,1,0,1,2,3,4,5,4], 0)
#
# def filter_spike_times(row):
#     s = [x for x in row.spike_times_trough
#          if len([y for y in row.spike_times if (y < x) and (y > x-2)]) == 1]
#     return s


def get_peaks_above(t, v, lim):
    assert len(t) == len(v)
    v, t = I.np.array(v), I.np.array(t)
    left_diff = v[1:-1] - v[:-2]
    right_diff = v[1:-1] - v[2:]
    values = v[1:-1]
    # use >= because sometimes the spikes reach the threashold of the amplifier of +5mV
    # by >, they would not be detected
    indices = I.np.argwhere((left_diff >= 0) & (right_diff >= 0) &
                            (values > lim)).ravel() + 1

    return list(t[indices]), list(v[indices])


#     for lv in I.np.argwhere(I.np.array(v) > lim).ravel():
#         try:
#             #for lv in range(1, len(t) - 1):
#             if (v[lv] > v[lv - 1]) and (v[lv] > v[lv + 1]):
#                 if v[lv] > lim:
#                     out_t.append(t[lv])
#                     out_v.append(v[lv])
#         except IndexError:
#             if (lv == 0) or (lv == len(v) - 1):
#                 continue
#             else:
#                 raise
#
#     return out_t, out_v
get_peaks_above([0, 1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 0, 1, 2, 3, 4, 5, 4], 0.5)


def filter_spike_times(spike_times, spike_times_trough):
    '''expects spike times defined by creast and trough.
    filters spike times: a spike is defined by its trough. it is only a spike, if there is a
    creast at max 2ms before the trough. the spike time is the first matching creast.'''
    #s = [x for x in row.spike_times_trough
    #     if len([y for y in row.spike_times if (y < x) and (y > x-2)]) >= 1]
    s = []
    spike_times = I.np.array(spike_times)
    for x in spike_times_trough:
        aligned_creasts = spike_times[(spike_times >= x - 2) & (
            spike_times
            < x)]  # [y for y in spike_times if (y < x) and (y >= x-2)]
        if len(aligned_creasts) > 0:
            s.append(aligned_creasts.max())  # before: aligned_creats[0]

    return s


def filter_short_ISIs(t, tdelta=0):
    '''filters out any events that occur in an interval shorter than tdelta
    '''
    if len(t) == 0:
        return []

    out_t = [t[0]]

    for tt in t[1:]:
        if tt - out_t[-1] > tdelta:
            out_t.append(tt)

    return out_t


assert filter_short_ISIs([0, 1, 2, 3, 4, 5, 6, 7, 8],
                         tdelta=1) == [0, 2, 4, 6, 8]


def strip_st(st):
    '''returns spike times dataframe only containing spike times, without metadata'''
    return st[[c for c in st.columns if I.utils.convertible_to_int(c)]]


def stimulus_injterval_filter(intervals):
    max_interval = max(set(I.np.diff(intervals).round()))
    out = []
    for i in intervals:
        if out:
            if i - out[-1] < max_interval - 5:
                continue
        out.append(i)
    return out


stimulus_injterval_filter([10, 20, 40, 50, 70, 80, 100])


def _find_stimulus_interval(stim_times):
    return stim_times[1] - stim_times[0]


def get_n_bursts(spike_times, n=5):
    out = []
    #n = min(n, len(spike_times))
    for lv in range(len(spike_times)):
        time = spike_times[lv]
        ISIs = {}
        for nn in range(1, n):
            try:
                spike_times[lv + nn]
            except IndexError:
                continue
            ISIs['ISI_{}'.format(nn)] = spike_times[lv + nn] - time
        ISIs['event_time'] = time
        out.append(ISIs)
    return I.pd.DataFrame(out)


def burst_analysis_2(row):
    event_maxtimes = {0: 0, 1: 10, 2: 30}  #+ , 3: 50, 4: 50}
    evnet_name = {
        0: 'singlet',
        1: 'doublet',
        2: 'triplet'
    }  #, 3: 'quadruplet', 4:'quintuplet'}
    row = I.np.array(row)
    out = []
    lv = 0
    while True:
        row_section = row[lv:]
        if len(row_section) == 0:
            break

        isis = row_section - row_section[0]
        for n in range(min(len(row_section) - 1, 2), -1, -1):
            if n > len(isis):
                continue
            if isis[n] <= event_maxtimes[n]:
                break

        out_dict = {'ISI_{}'.format(nn): isis[nn] for nn in range(n + 1)}
        out_dict['event_time'] = row_section[0]
        out_dict['event_class'] = evnet_name[n]

        out.append(out_dict)
        lv += 1 + n
    return I.pd.DataFrame(out)


# burst_analysis_2([1,2,3,4,5,80, 81, 82, 133])


def get_spike_times_from_row(row):
    row = row.dropna()
    row = [v for i, v in row.iteritems()]
    return row


class EventAnalysis:

    def __init__(self, st):
        self.st = st
        st.cellid
        st = strip_st(st)
        # self.spike_times = st.apply(get_spike_times_from_row, axis = 1)
        dummy = [(name, get_spike_times_from_row(row))
                 for name, row in st.iterrows()]
        self.spike_times = I.pd.Series([d[1] for d in dummy],
                                       index=[d[0] for d in dummy])
        self.event_types = []
        self.event_extractors = {}
        self.event_db = {
        }  # schema event_type, trial, event_time, event_parameters
        self.apply_extractor(get_n_bursts)
        self.apply_extractor(burst_analysis_2)
        self.update()

    def apply_extractor(self, event_extractor):
        extractor_name = event_extractor.__name__
        out = []
        for name, spike_times in self.spike_times.iteritems():
            df = event_extractor(spike_times)
            df['trial'] = name
            df['cellid'] = self.st.loc[name].cellid
            df['event_type'] = extractor_name
            out.append(df)
        out = I.pd.concat(out).reset_index(drop=True)
        self.event_db[extractor_name] = out
        return out

    def update(self):
        self.visualize = VisualizeEventAnalysis(self)


import six


def get_interval(interval_dict, t):
    for i, v in six.iteritems(interval_dict):
        if (t >= v[0]) and (t < v[1]):
            return i


class VisualizeEventAnalysis:

    def __init__(self, ea):
        self.ea = ea

    def plot_PSTH(self, min_time=0, max_time=2500, bin_size=5):
        st = self.ea.st
        bins = I.temporal_binning(st, min_time=0, max_time=2500, bin_size=5)
        fig = I.plt.figure()
        I.histogram(bins, fig=fig.add_subplot(111))
        ax = fig.axes[-1]
        ax.set_xlabel('t / ms')
        ax.set_ylabel('# spikes / trial / ms')
        ax.set_ylim([0, 0.5])
        I.sns.despine()
        return fig

    def plot_ISI1_vs_ISI2(self,
                          interval_dict,
                          rp=2.5,
                          color_dict=I.defaultdict(lambda: 'k'),
                          ax1=None,
                          ax2=None):

        # color_dict = {'ongoing': 'grey', 'onset': 'r', 'sustained': 'k', 'late': 'green', None: 'white'}
        colormap = {
            10: 'r',
            20: 'orange',
            30: 'green',
            40: 'blue',
            50: 'purple'
        }
        e = self.ea.event_db['get_n_bursts']
        tmax = interval_dict['late'][1]
        e = e[e.event_time < tmax]
        if (ax1 is None) or (ax2 is None):
            fig = I.plt.figure(figsize=(6, 3), dpi=200)
            ax1 = fig.add_subplot(121)
            ax2 = fig.add_subplot(122)

        colors = [
            color_dict[get_interval(interval_dict, t)] for t in e.event_time
        ]
        ax1.scatter(e.ISI_1, e.ISI_2 - e.ISI_1, color=colors, marker='.')
        ax1.set_xlabel('ISI first to second spike')
        ax1.set_ylabel('ISI second to third spike')
        ax1.plot([rp, rp], [0, 100], c='grey')
        ax1.plot([0, 100], [rp, rp], c='grey')
        import six
        for name, c in six.iteritems(colormap):
            if c == 'white':
                continue
            ax1.plot([0, name], [name, 0], c=c, linewidth=.5)

        ax1.set_aspect('equal')
        ax1.set_xlim(0, 30)
        ax1.set_ylim(0, 30)
        import six

        for name, c in six.iteritems(colormap):
            if name > 30:
                continue
            e_filtered = e[(e.ISI_2 < name) & (e.ISI_2 >= name - 10)]
            print(name, len(e_filtered))
            if len(e_filtered) == 0:
                print('skipping')
                continue
            e_filtered.event_time.plot(kind='hist',
                                       bins=I.np.arange(0, tmax, 1),
                                       cumulative=True,
                                       histtype='step',
                                       color=c,
                                       ax=ax2,
                                       normed=False)
        ax2.set_xlabel('t / ms')
        #ax2.axvline(700, color = 'grey')

        I.sns.despine()

    def plot(self):
        for k in dir(self):
            if k.startswith('plot_'):
                getattr(self, k)()


class AnalyzeFile:

    def __init__(self,
                 path,
                 lim_creast='minimum',
                 lim_trough='minimum',
                 cellid='__no_cellid_assigned__',
                 periods={'1onset': (0, 100)},
                 analogsignal_id=0,
                 stim_times_channel='5',
                 tdelta=1):
        ''' Class for automatic analysis of smr files.
        
        periods: requires '1onset' as key for plot_n_onset function.
        '''
        self.lim_creast = lim_creast
        self.lim_trough = lim_trough
        self.path = path
        self.analogsignal_id = analogsignal_id
        self.tdelta = tdelta

        # read smr file
        self.data = data = read_smr_file(path)

        ## extract voltage trace
        asig = data.segments[0].analogsignals[analogsignal_id]
        self.t = t = asig.times.rescale('s').magnitude.flatten() * 1000
        self.v = v = asig.magnitude.flatten()
        self.periods = periods

        ## extract events
        self.events = events = {
            e.annotations['id']: e for e in data.segments[0].events
        }

        # stim_times
        stim_times = I.np.array(events[stim_times_channel]) * 1000
        self.stim_times = stimulus_injterval_filter(stim_times)
        if len(stim_times) > len(self.stim_times):
            print('multi-stimulus detected. using period {}'.format(
                I.np.diff(self.stim_times)[0]))

        # automatic detection of creast and trough limit
        if isinstance(lim_creast, str):
            assert isinstance(lim_trough, str)
            lim_creast, lim_trough = self.get_creast_and_trough_ampltidues_by_bins(
                lim_creast)
            self.lim_creast = lim_creast
            self.lim_trough = lim_trough

        # spike_times
        _st, _st_magnitude = get_peaks_above(
            t, v, lim_creast)  # spike times detected by creast
        _stt, _stt_magnitude = get_peaks_above(
            t, v * -1, lim_trough * -1)  # spike times detected by trough
        self.spike_times = filter_spike_times(_st, _stt)
        self.spike_times = filter_short_ISIs(self.spike_times, tdelta=tdelta)

        # generate spike_time dataframe
        self.master_pdf_row = I.pd.Series({
            'stim_times': self.stim_times,
            'spike_times': self.spike_times
        })
        self.st = st = get_st_from_spike_times_and_stim_times(
            cellid, self.spike_times, self.stim_times)
        if (st.shape[1] == 1):
            st[1] = I.np.NaN
        print('self.st.shape', self.st.shape)
        self.st['cellid'] = cellid
        st = self.st
        if (st.shape[1] == 1):
            st[1] = I.np.NaN

        # run event_analysis

        self.ea = EventAnalysis(st)
        df = self.ea.event_db['burst_analysis_2']
        df['experiment'] = cellid
        df['period'] = df.apply(
            lambda x: get_period_label_by_time(self.periods, x.event_time),
            axis=1)
        self.event_df = df

    def get_ongoing_activity(self, period_prestim=30000):
        if self.stim_times[0] < period_prestim:
            s = self.stim_times[0]
            print(
                'warning! there are no {} s activity pre stimulus. Falling back to {}s'
                .format(period_prestim / 1000., s / 1000.))
        else:
            s = period_prestim
        return len([
            t for t in self.spike_times if (t < self.stim_times[0]) and
            (t > self.stim_times[0] - s)
        ]) / (s / 1000.)

    def get_onset_latency(self):
        return I.np.median([
            s for s in self.st[0]
            if self.periods['1onset'][0] <= s <= self.periods['1onset'][1]
        ])

    def describe(self):
        af = self
        text = 'n trials: {} '.format(af.st.shape[0])
        text += '\n' + 'ongoing activity: {} Hz'.format(
            af.get_ongoing_activity())
        text += '\n' + 'onset spike prob: {}'.format(
            af.get_onset_spike_probability())
        text += '\n' + 'onset spike latency: {} ms'.format(
            af.get_onset_latency())
        text += '\n' + 'creast / trough limit [mV]: {} / {}'.format(
            af.lim_creast, af.lim_trough)
        return text

    def get_onset_spike_probability(self):
        return I.spike_in_interval(self.st, *self.periods['1onset']).mean()

    def plot_spike_amplitude_histograms(self, ax=None):
        _st, _st_magnitude, _stt, _stt_magnitude = self.get_peaks_and_peak_amplitudes(
        )
        ax.hist(_st_magnitude, bins=I.np.arange(-7, 7, 0.1))
        ax.hist(I.np.array(_stt_magnitude) * -1, bins=I.np.arange(-7, 7, 0.1))
        ax.axvline(self.lim_creast)
        ax.axvline(self.lim_trough)
        ax.set_yscale('log')
        ax.set_xlabel('detected creast and trough amplitudes / mV')

    def _get_fig(self, ax=None):
        if ax is not None:
            return ax
        else:
            fig = I.plt.figure()
            return fig.add_subplot(111)

    def plot_onset_latency(self, ax=None):
        ax = self._get_fig(ax)
        onset_end = 100  # self.periods['1onset'][1]
        ax.axvspan(*self.periods['1onset'], color='lightgrey')
        ax.hist(self.st[0].dropna().values, bins=I.np.arange(0, onset_end, 1))
        ax.set_xlabel('onset latency / ms')

    def get_df(self, groupby=['period'], normed=False):

        df = self.event_df

        column_order = [
            'singlet', 'doublet', 'triplet', 'quadruplet', 'quintuplet'
        ]
        _ = df.groupby(groupby).apply(lambda x: x.event_class.value_counts())

        if isinstance(_, I.pd.Series):  # this happens, if
            _ = _.unstack(-1)
        _ = _.fillna(0)

        if normed:
            _ = _.apply(lambda x: x / x.sum(), axis=1)
        column_order = [c for c in column_order if c in _.columns]
        return _[column_order]

    def get_table(self, groupby=['period']):
        mean_ = self.get_df(groupby, normed=True)
        mean_unnormed = self.get_df(groupby, normed=False)
        return mean_, mean_unnormed

    def plot_burst_fractions(self, ax=None):
        mean_, mean_unnormed = self.get_table()
        ax = self._get_fig(ax)

        d = mean_
        d = d.fillna(0).stack().to_frame(name='n')
        d['period'] = d.index.get_level_values(0)
        d['type'] = d.index.get_level_values(1)

        with I.pd.option_context("display.max_rows", 1000):
            I.display.display(mean_.round(2))
            I.display.display(mean_unnormed.round(2))
        I.sns.barplot(data=d, x='period', y='n', hue='type', ax=ax)
        ax.set_ylim([0, 1])
        I.plt.ylabel('% of spiking activity')
        ax.legend()

    def get_n_onset2(self):
        af = self
        tmin, tmax = af.periods['1onset']

        df = af.event_df
        len_ = af.st.shape[0]
        out = I.pd.Series([0] * len_)

        df = df[(df.event_time >= tmin) & (df.event_time < tmax)]
        df['trial'] = df.trial.str.split('/').str[1].astype(int)
        df = df.set_index('trial')
        out2 = df.event_class.map({
            'singlet': 1,
            'doublet': 2,
            'triplet': 3,
            'quadruplet': 4,
            'quintuplet': 5
        })

        out[out2.index] = out2.values
        return out

    def get_peaks_and_peak_amplitudes(self):
        '''returns: times of creasts, creast amplitudes, timepoints of troughs, trough amplitudes.
            These are computed in the timespan from first stimulus - 3s till last stimulus + 3s '''
        t = [
            t for t in self.t if (t > self.stim_times[0] -
                                  3000) and (t < self.stim_times[-1] + 3000)
        ]
        v = [
            v for tt, v in zip(self.t, self.v)
            if (tt > self.stim_times[0] - 3000) and (tt < self.stim_times[-1] +
                                                     3000)
        ]
        t, v = I.np.array(t), I.np.array(v)
        assert len(t) == len(v)
        _st, _st_magnitude = get_peaks_above(t, v, 0)
        _stt, _stt_magnitude = get_peaks_above(t, v * -1, 0)
        return _st, _st_magnitude, _stt, _stt_magnitude

    def get_creast_and_trough_ampltidues_by_bins(self, mode='zero'):
        _st, _st_magnitude, _stt, _stt_magnitude = self.get_peaks_and_peak_amplitudes(
        )
        bins = I.np.arange(0, 7, 0.1)
        binned_data_st, _ = I.np.histogram(_st_magnitude, bins=bins)
        binned_data_sst, _ = I.np.histogram(_stt_magnitude, bins=bins)
        if mode == 'zero':
            minimun_zero_bin_st = bins[I.np.argwhere(binned_data_st == 0).min()]
            minimun_zero_bin_sst = bins[I.np.argwhere(
                binned_data_sst == 0).min()]
        elif mode == 'minimum':
            minimun_zero_bin_st = bins[I.np.argwhere(
                ((binned_data_st[4:-1] - binned_data_st[5:]) < 0) |
                (binned_data_st[4:-1] == 0)).min() + 4]
            minimun_zero_bin_sst = bins[I.np.argwhere(
                ((binned_data_sst[4:-1] - binned_data_sst[5:]) < 0) |
                (binned_data_st[4:-1] == 0)).min() + 4]
        return minimun_zero_bin_st, minimun_zero_bin_sst * -1

    def plot_n_onset(self, ax=None):
        ax = self._get_fig(ax)
        o = self.get_n_onset2().fillna(0)
        o.plot(ax=ax, c='grey', label='__no_legend__', alpha=1, linewidth=.5)
        o.rolling(window=15).mean().plot(ax=ax, alpha=1, linewidth=1, color='k')
        ax.set_ylim(-.5, 4)
        ax.set_xlabel('# trial')
        ax.set_ylabel('# onset spikes')

    def plot_PSTH(self, ax=None):
        ax = self._get_fig(ax)
        ax.set_xlabel('t / ms')
        ax.set_ylabel('# spikes / ms / trial')
        bins = I.temporal_binning(self.st, min_time=0)
        I.histogram(bins, fig=ax)

    def plot_all_flat(self):
        af = self
        fig = I.plt.figure(figsize=(25, 3))
        af.plot_spike_amplitude_histograms(ax=fig.add_subplot(151))
        af.plot_onset_latency(ax=fig.add_subplot(152))
        af.plot_PSTH(ax=fig.add_subplot(153))
        af.plot_burst_fractions(ax=fig.add_subplot(154))
        af.plot_n_onset(ax=fig.add_subplot(155))
        I.plt.tight_layout()
        I.sns.despine()

    def plot_all_stacked(self, text=''):
        text = text + self.describe()
        af = self
        fig = I.plt.figure(figsize=(15, 4))
        ax = fig.add_subplot(231)
        ax.text(0, 0, text)
        ax.axis('off')
        ax.set_ylim(-1, 1)
        af.plot_spike_amplitude_histograms(ax=fig.add_subplot(234))
        af.plot_onset_latency(ax=fig.add_subplot(235))
        af.plot_PSTH(ax=fig.add_subplot(232))
        af.plot_burst_fractions(ax=fig.add_subplot(236))
        af.plot_n_onset(ax=fig.add_subplot(233))
        I.plt.tight_layout()
        I.sns.despine()

    def show_events(self, type_, savedir=None, display=True, close=True):
        af = self
        df = self.event_df
        df = df[df.event_class == type_].copy()
        if len(df) == 0:
            print('nothing to show')
            return
        df['trial_index'] = df.trial.str.split('/').str[1].astype(int)
        df['absolute_time'] = df.apply(
            lambda x: x.event_time + af.stim_times[x.trial_index], axis=1)
        event_time = df.absolute_time

        for n in range(0, len(event_time)):
            offset_time = event_time.values[n]
            fig = I.plt.figure(figsize=(15, 4))
            I.plt.plot(af.t, af.v)  ###
            for t in self.stim_times:
                I.plt.axvline(t, color='r', linewidth=.5)
            for t in self.spike_times:

                if offset_time - 50 <= t <= offset_time + 70:
                    v = I.np.interp([t], af.t, af.v)
                    #I.plt.plot([t], v, '|', color = 'grey')
                    I.plt.axvline(t, color='grey', linewidth=.5)
            I.plt.axhline(self.lim_creast, color='grey', linewidth=.5)
            I.plt.axhline(self.lim_trough, color='grey', linewidth=.5)

            I.plt.xlim(offset_time - 10, offset_time + 50)
            I.plt.gca().ticklabel_format(useOffset=False)
            # I.plt.gca().set_xticks([offset_time + 10 * x for x in range(10)])
            # _ = I.plt.gca().set_xticklabels([10 * x for x in range(10)])
            I.sns.despine()
            I.plt.ylim(-5, 5)
            I.plt.xlabel('t / ms')
            I.plt.ylabel('recorded potential / mV')
            I.plt.title('{}, {}'.format(df.event_class.values[n],
                                        df.period.values[n]))

            if display:
                I.display.display(fig)
            if savedir:
                fig.savefig(
                    I.os.path.join(
                        savedir, '{}_{}_{}ms_creast_{}_trough{}.pdf'.format(
                            type_, df.period.values[n], int(offset_time),
                            self.lim_creast, self.lim_trough)))
            if close:
                I.plt.close()


# path = '/nas1/Data_Mike/LongRange_Inputs/VPM_Analysis/WR71_Cell5_L5Int/Physiology/Cell2_1083um_Ongoing_AirPuff_Trial1_Data.smr'

# af = AnalyzeFile(path, stim_times_channel='3')
