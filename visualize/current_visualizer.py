from biophysics_fitting import get_main_bifurcation_section
from . import np
from . import plt

COLORMAP = {
    'Ca_HVA.ica': '#4682C3',
    'Ca_LVAst.ica': '#ACD7E4',
    'Ih.ihcn': '#838383',
    'Im.ik': '#F2E500',
    'NaTa_t.ina': '#EE781C',
    'SK_E2.ik': '#06652E',
    'SKv3_1.ik': '#9BC985'
}

CALCIUM_ORANGE = '#f9b233'


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
                sec = get_main_bifurcation_section(cell)
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
        self.colormap = colormap if colormap else COLORMAP
        # compute currents
        self._compute_current_arrays()

    def _get_current_by_rv(self, rv):
        try:
            if self.mode == 'dict':
                return self.cell[rv]
            elif self.mode == 'cell':
                return np.array(self.sec.recordVars[rv][self.segID])
            else:
                raise ValueError()
        except (KeyError, IndexError):
            return np.array([float('nan')] * len(self.t))

    def _compute_current_arrays(self):
        out_depolarizing = []
        out_hyperpolarizing = []
        for rv in self.rangeVars:
            x = self._get_current_by_rv(rv)
            out_depolarizing.append(np.where(x >= 0, 0, x))
            out_hyperpolarizing.append(np.where(x < 0, 0, x))
        self.depolarizing_currents = np.array(out_depolarizing) * -1
        self.hyperpolarizing_currents = np.array(out_hyperpolarizing) * -1
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
        t = np.array(self.t) - t_stim
        if ax is None:
            fig = plt.figure(figsize=(10, 4), dpi=200)
            ax = fig.add_subplot(111)

        def __helper(currents, plot_label=True):
            dummy = np.cumsum(currents, axis=0)
            dummy = np.vstack([np.zeros(dummy.shape[1]), dummy])
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
            x, y = t[select], np.array(self.cell.soma.recVList[0])[select]
            ax2.plot(x, y, 'k')
            x, y = t[select], np.array(self.voltage_trace)[select]
            ax2.plot(x, y, c=CALCIUM_ORANGE)
        ax2.set_ylabel("Membrane potential (mV)")
        ax.set_ylabel("Current (nA)")
        ax.set_xlabel("Time (ms)")
        plt.legend()

    def plot_lines(self, ax=None, legend=True):
        if ax is None:
            fig = plt.figure(figsize=(15, 6))
            ax = fig.add_subplot(111)
        for name in self.rangeVars:
            ax.plot(self.t,
                    np.array(self.sec.recordVars[name][self.segID]) * -1,
                    label=name)
