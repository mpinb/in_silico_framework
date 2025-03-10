"""Visulize all transmembrane ionic currents of a cell simulation.


This module provides a class to visualize the transmembrane ionic currents of a cell simulation.
It assumes that these have been recorded during the simulation. If this was not the case,
consider re-simulating the cell and recording the currents, e.g. with a :py:class:`~biophysics_fitting.simulator.Simulator`.

Example:

    >>> def record_rangevars(cell, params):
    ...     for rv in record_vars:
    ...         cell.record_range_var(rv)
    ...     return cell
    >>> simulator.setup.cell_modify_funs.append(('BAC.record_range_vars', record_rangevars))
    >>> cell, _ = simulator.get_simulated_cell(biophysical_parameters, stim="BAC")
    >>> ca = CurrentAnalysis(cell)
    >>> ca.plot_areas()
    
.. figure:: ../../../_static/_images/current_analysis.png

    Example of a current analysis plot for a :py:class:`~biophysics_fitting.hay_evaluation_python.BAC` stimulus, simulated with a :py:class:`~biophysics_fitting.simulator.Simulator`.

"""


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
    """Plot the individual ion currents and the net current of a cell simulation.
    
    Inspect the individual ion currents and the net current of a single cell segment.
    
    Attributes:
        mode (str): 'cell' or 'dict'.
        cell (:py:class:`~single_cell_parser.cell.Cell` | dict): The cell object, or a dictionary containing equivalent simulation data.
        t (list): The time vector.
        sec (Section): The section of the cell.
        secID (int): The index of the section.
        segID (int): The index of the segment.
        seg (Segment): The segment of the cell.
        rangeVars (list): The names of the ion currents to plot. Default is `None`, which plots all ion currents.
        colormap (dict): The colormap for the ion currents.
        depolarizing_currents (np.array): The depolarizing currents.
        hyperpolarizing_currents (np.array): The hyperpolarizing currents.
        depolarizing_currents_sum (np.array): The sum of the depolarizing currents.
        hyperpolarizing_currents_sum (np.array): The sum of the hyperpolarizing currents.
        net_current (np.array): The net current.
        depolarizing_currents_normalized (np.array): The normalized depolarizing currents.
        hyperpolarizing_currents_normalized (np.array): The normalized hyperpolarizing currents.
        voltage_trace (np.array): The voltage trace.
    """

    def __init__(
        self,
        cell_or_dict=None,
        secID='bifurcation',
        segID=-1,
        rangeVars=None,
        colormap=None,
        tVec=None):
        """Initialize the CurrentAnalysis object.
        
        Args:
            cell_or_dict (dict or Cell): The cell object, or a dictionary containing equivalent simulation data.
            secID (int): The index of the section. Default is 'bifurcation'.
            segID (int): The index of the segment. Default is -1.
            rangeVars (list): The names of the ion currents to plot. Default is `None`, which plots all ion currents.
            colormap (dict): The colormap for the ion currents. Default is `None`.
            tVec (list): The time vector. Default is `None`. Only necessary if :paramref:`cell_or_dict` is a dictionary.
        """
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
        """Get the section current by the range variable name.
        
        Args:
            rv (str): The range variable name.
              
        Returns:
            np.array: The ionic current of the section.
        """
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
        """Compute the ionic currents of a section.

        Updates the following attributes:
        
        - depolarizing_currents (np.array): The depolarizing currents.
        - hyperpolarizing_currents (np.array): The hyperpolarizing currents.
        - depolarizing_currents_sum (np.array): The sum of the depolarizing currents.
        - hyperpolarizing_currents_sum (np.array): The sum of the hyperpolarizing currents.
        - net_current (np.array): The net current.
        - depolarizing_currents_normalized (np.array): The normalized depolarizing currents.
        - hyperpolarizing_currents_normalized (np.array): The normalized hyperpolarizing currents.
        - voltage_trace (np.array): The voltage trace.
        
        """
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

    def plot_areas(
            self,
            ax=None,
            normalized=False,
            plot_net=False,
            plot_voltage=False,
            t_stim=295,
            select_window_relative_to_stim=(0, 55)
        ):
        """Plot the ion currents and the net current of a cell simulation.
        
        Args:
            ax (Axes): The matplotlib axes object. Default is `None`.
            normalized (bool): Whether to plot the normalized currents. Default is `False`.
            plot_net (bool): Whether to plot the net current. Default is `False`.
            plot_voltage (bool): Whether to plot the voltage trace. Default is `False`.
            t_stim (int): The time of the stimulus. Default is 295.
            select_window_relative_to_stim (tuple): The time window to select relative to the stimulus time. Default is (0, 55).
            
        Returns:
            None
        """
        t = np.array(self.t) - t_stim
        if ax is None:
            fig = plt.figure(figsize=(10, 4), dpi=200)
            ax = fig.add_subplot(111)

        def __helper(ax, currents, plot_label=True):
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
            __helper(ax, self.depolarizing_currents_normalized)
            __helper(ax, self.hyperpolarizing_currents_normalized, plot_label=False)
            ax.plot(t, self.depolarizing_currents_sum + 1, c='k')
            ax.plot(t, self.hyperpolarizing_currents_sum - 1, c='k')
        else:
            __helper(ax, self.depolarizing_currents)
            __helper(ax, self.hyperpolarizing_currents, False)
        if plot_net:
            ax.plot(t, self.net_current, 'k', label='net current')
        ax.set_ylabel("Current (nA)")
        ax.set_xlabel("Time (ms)")
        plt.legend()

        if plot_voltage:
            ax2 = ax.twinx()
            select = (t >= select_window_relative_to_stim[0]) & (
                t <= select_window_relative_to_stim[1])
            x, y = t[select], np.array(self.cell.soma.recVList[0])[select]
            ax2.plot(x, y, 'k')
            x, y = t[select], np.array(self.voltage_trace)[select]
            ax2.plot(x, y, c=CALCIUM_ORANGE)
        ax2.set_ylabel("Membrane potential (mV)")
        return fig

    def plot_lines(self, ax=None, legend=True):
        """Plot the ion currents and the net current of a cell simulation.
        
        Args:
            ax (Axes): The matplotlib axes object. Default is `None`.
            legend (bool): Whether to plot the legend. Default is `True`.
            
        Returns:
            None
        """
        if ax is None:
            fig = plt.figure(figsize=(15, 6))
            ax = fig.add_subplot(111)
        for name in self.rangeVars:
            ax.plot(self.t,
                    np.array(self.sec.recordVars[name][self.segID]) * -1,
                    label=name)
