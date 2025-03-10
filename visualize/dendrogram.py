"""Plot a dendrogram of a neuron morphology.

Dendrograms are schematic representations of neuron morphologies.
This module provides a class to plot dendrograms, as well as denddritic length and synapse count statistics.

.. figure:: ../../../_static/_images/dendrogram.png
"""
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection

from biophysics_fitting import get_main_bifurcation_section
from visualize.histogram import histogram


def range_overlap(beginning1, end1, beginning2, end2, bool_=True):
    """Check if two ranges overlap.

    :skip-doc:

    Args:
        beginning1 (float): The beginning of the first range.
        end1 (float): The end of the first range.
        beginning2 (float): The beginning of the second range.
        end2 (float): The end of the second range.
        bool\_ (bool): Whether to return a boolean value. Default is `True`.

    Returns:
        float | bool: The overlap of the two ranges, or a boolean value if `bool_` is set to `True`.
    """
    out = min(end1, end2) - max(beginning1, beginning2)
    out = max(0, out)
    if bool_:
        out = bool(out)
    return out


def get_dist(x1, x2):
    """Get the distance between two points.

    :skip-doc:

    Args:
        x1 (list): The first point.
        x2 (list): The second point.

    Returns:
        float: The Euclidean distance between the two points.
    """
    assert len(x1) == len(x2)
    return np.sqrt(sum((xx1 - xx2) ** 2 for xx1, xx2 in zip(x1, x2)))


def _get_max_somadistance(dendrogram_db):
    """Get the coordinate of the point that is furthest away from the soma.

    Args:
        dendrogram_db (list): A list of :py:class:`_DendrogramSection` objects.

    Returns:
        float: The coordinate of the point that is furthest away from the soma.
    """
    out = 0
    for dendro_section in dendrogram_db:
        out = max(out, dendro_section.x_dist_end)
    return out


def _get_db_by_sec(dendrogram_db, sec):
    """Get the :py:class:`_DendrogramSection` object by its section ID.

    Args:
        sec (int): The section ID.

    Returns:
        :py:class:`_DendrogramSection`: The dendrogram section.
    """
    return next(
        dendro_section for dendro_section in dendrogram_db if dendro_section.sec == sec
    )


class _DendrogramSection:
    """A class to represent a dendrogram section.

    A dendrogram section is a single neuron section, as it is represented in a dendrogram.
    It does not necessarily contain any morphological information.
    The usecase of this class is to be a leightweight dataclass, used in the :py:class:`Dendrogram` and :py:class:`DendrogramStatistics` classes.


    Attributes:
        name (str): The name of the section.
        x_dist_start (float): The starting distance of the section in :math:`\mu m`.
        x_dist_end (float): The ending distance of the section in :math:`\mu m`.
        sec (:py:class:`~single_cell_parser.cell.PySection`): The neuron section.
        synapses (dict): A dictionary of synapses in the section.
        main_bifurcation (bool): Whether the section is the main bifurcation. Default is `False`.
        sec_id (int): The section id of the section.
    """

    def __init__(
        self,
        name,
        x_dist_start,
        x_dist_end,
        sec,
        main_bifurcation=False,
        sec_id=None,
    ):
        """
        Args:
            name (str): The name of the section.
            x_dist_start (float): The starting distance of the section in :math:`\mu m`.
            x_dist_end (float): The ending distance of the section in :math:`\mu m`.
            sec (:py:class:`~single_cell_parser.cell.PySection`): The neuron section.
            main_bifurcation (bool): Whether the section is the main bifurcation. Default is `False`.
            sec_id (int): The section id of the section.
        """
        self.name = name
        self.x_dist_start = x_dist_start
        self.x_dist_end = x_dist_end
        self.sec = sec
        self.synapses = {}
        self.main_bifurcation = main_bifurcation
        self.sec_id = sec_id

    def _add_synapse(self, label, x):
        """Add a synapse to a dendrogram section.

        Args:
            label (str): The label of the synapse.
            x (float): The coordinate of the synapse.
        """
        if not label in self.synapses:
            self.synapses[label] = []
        self.synapses[label].append(x)


class Dendrogram:
    """Plot a dendrogram of a :py:class:`~single_cell_parser.cell.Cell` object.

    Dendrograms are schematic representations of neuron morphologies.

    Example::

        >>> d = Dendrogram(cell)
        >>> ax = d.plot()
        >>> ax.set_xlabel('Distance from soma ($\mu m$)')

    .. figure:: ../../../_static/_images/dendrogram.png

    Attributes:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        dendrogram_db (list): A list of :py:class:`_DendrogramSection` objects.
        dendrogram_db_by_name (dict): A dictionary of dendrogram sections by name.
        dendrogram_db_by_sec_id (dict): A dictionary of dendrogram sections by section ID.
        main_bifur_dist (float): The distance to the main bifurcation, in :math:`\mu m`.
    """

    def __init__(self, cell):
        """
        Args:
            cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        """
        self.cell = cell
        self.dendrogram_db = []
        self._cell_to_dendrogram(basesec=self.cell.soma)
        self._soma_to_dendrogram(self.cell)
        self.dendrogram_db_by_name = {d_.name: d_ for d_ in self.dendrogram_db}
        self.dendrogram_db_by_sec_id = {int(d_.sec_id): d_ for d_ in self.dendrogram_db}
        self._compute_main_bifurcation_section()

    def plot(self, ax=None):
        """Plot the dendrogram.

        Args:
            ax (:py:class:`matplotlib.axes.Axes`): The matplotlib axes object. Default is `None` and a new figure is created.

        Returns:
            :py:class:`matplotlib.axes.Axes`: The matplotlib axes object.
        """
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)
        ax = self._plot_dendrogram(ax)
        return ax

    def get_parent_by_name(self, name):
        """Get the parent of a dendrogram section by its name.

        Args:
            name (str): The name of the section.

        Returns:
            :py:class:`_DendrogramSection`: The parent dendrogram section. None if the section is the soma.
        """
        sec = self.dendrogram_db_by_name[name].sec.parent
        if sec.label == "Soma":
            return None
        else:
            return _get_db_by_sec(self.dendrogram_db, sec)

    def _compute_main_bifurcation_section(self):
        """Compute the main bifurcation section of the dendrogram.

        The main bifurcation section is highlighted on the dendogram.

        :skip-doc:
        """
        try:
            sec = get_main_bifurcation_section(self.cell)
        except AssertionError:
            print("main bifurcation could not be identified!")
            self.main_bifur_dist = None
        else:
            dendro_section = _get_db_by_sec(self.dendrogram_db, sec)
            dendro_section.main_bifurcation = True
            self.main_bifur_dist = dendro_section.x_dist_end

    def _cell_to_dendrogram(self, basesec=None, basename="", x_dist_base=0):
        """Convert a cell to a dendrogram.

        :skip-doc:
        """
        if basename:
            basename = basename.split("__")
        else:
            basename = ("", "", "")
        for lv, sec in enumerate(sorted(basesec.children(), key=lambda x: x.label)):
            if sec.label not in ("Dendrite", "ApicalDendrite", "Soma"):
                continue

            x_dist_start = x_dist_base
            x_dist_end = x_dist_start + sec.L

            name = (
                sec.label
                + "__"
                + (basename[1] + "_" if basename[1] else "")
                + str(lv)
                + "__"
                + str(np.round(sec.L))
            )
            self.dendrogram_db.append(
                _DendrogramSection(
                    name=name,
                    x_dist_start=x_dist_start,
                    x_dist_end=x_dist_end,
                    sec=sec,
                    sec_id=sec.secID,
                )
            )

            self._cell_to_dendrogram(basesec=sec, basename=name, x_dist_base=x_dist_end)

    def _soma_to_dendrogram(self, cell):
        """Convert the soma to a dendrogram.

        :skip-doc:
        """
        soma_sections = [s for s in cell.sections if s.label.lower() == "soma"]
        for lv, sec in enumerate(soma_sections):
            self.dendrogram_db.append(
                _DendrogramSection(
                    name="Soma__{}__0".format(lv),
                    x_dist_start=np.nan,
                    x_dist_end=np.nan,
                    sec=sec,
                    sec_id=sec.secID,
                )
            )

    def _plot_dendrogram(
        self, ax, colormap={"Dendrite": "grey", "ApicalDendrite": "r"}
    ):
        """Plot the dendogram on an axes object.

        This is the main plotting method used to either plot the dendogram alone, or to plot the
        dendrogram in :py:class:`DendrogramStatistics`.

        Args:
            ax (:py:class:`matplotlib.axes.Axes`): The matplotlib axes object.

        Returns:
            :py:class:`matplotlib.axes.Axes`: The matplotlib axes object.
        """
        lines = []

        for sec_id, dendro_section in enumerate(self.dendrogram_db):
            label, tree, L = dendro_section.name.split("__")
            if label not in ["Dendrite", "ApicalDendrite"]:
                continue
            sec_id = dendro_section.sec_id
            parent = self.get_parent_by_name(dendro_section.name)
            parent_sec_id = parent.sec_id if parent is not None else 0

            # Collect lines for batch plotting
            lines.append(
                (
                    [dendro_section.x_dist_start, parent_sec_id],
                    [dendro_section.x_dist_start, sec_id],
                    [dendro_section.x_dist_end, sec_id],
                )
            )

            if dendro_section.main_bifurcation:
                ax.plot([dendro_section.x_dist_end], [dendro_section.sec_id], "o")

        # Plot all collected lines at once
        line_segments = LineCollection(
            lines, colors=[colormap.get(label, "k")] * len(lines), linewidths=0.5
        )
        ax.add_collection(line_segments)

        ax.set_ylabel("branch id")
        max_x = _get_max_somadistance(self.dendrogram_db)
        ax.set_xlim(-0.01 * max_x, max_x)
        ax.set_ylim(-5, len(self.dendrogram_db))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)

        return ax


class _DendrogramDendriteStatistics:
    """Compute dendrite statistics from a dendrogram.

    Dendrite statistics includes the total amount of dendritic length in a certain bin of soma distance.
    This is useful for calculating synapse statistics as well.

    Attributes:
        dendrogram_db (list): A list of :py:class:`_DendrogramSection` objects.
        colormap_synapses (dict): A dictionary mapping color to synapse types. The keys must match the synapse types in the dendrogram.
            Missing keys will be omitted from the visualization alltogether. Default: `None` (plot all synapses in black).
        bins (np.array): The bins of the dendrite density histogram.
        dendrite_density (np.array): The dendrite density histogram, i.e. the amount of dendritic length within a range of soma distance.

    """

    def __init__(self, dendrogram_db, colormap_synapses=None):
        """
        Args:
            dendrogram_db (list): A list of :py:class:`_DendrogramSection` objects.
            colormap_synapses (dict): A dictionary mapping color to synapse types. The keys must match the synapse types in the dendrogram.
                Missing keys will be omitted from the visualization alltogether. Default: `None` (plot all synapses in black).
        """
        if colormap_synapses is None:
            colormap_synapses = {}
        self.dendrogram_db = dendrogram_db
        self.colormap_synapses = colormap_synapses
        self.bins = None
        self.dendrite_density = None

    def plot(self, ax=None):
        """Plot the dendrite statistics.

        This method is usually not used alone. Its base method
        :py:meth:`~DendrogramdendriteStatistics._plot_dendrite_hist` is used to plot the dendrogram statistics.

        Args:
            ax (:py:class:`matplotlib.axes.Axes`): The matplotlib axes object. Default is `None` and a new figure is created.

        Returns:
            :py:class:`matplotlib.axes.Axes`: The matplotlib axes object.
        """
        ax = self._plot_dendrogram(ax)
        xlim = ax.get_xlim()
        self._plot_dendrite_hist(ax, xlim)
        return ax

    def _get_amount_of_dendrite_in_bin(self, min_, max_):
        """Get the amount of dendritic length in a certain bin of soma distance.

        Args:
            min\_ (float): The minimum soma distance.
            max\_ (float): The maximum soma distance.

        Returns:
            float: The amount of dendritic length in the bin.
        """
        out = 0
        for dendro_section in self.dendrogram_db:
            out += range_overlap(
                min_,
                max_,
                dendro_section.x_dist_start,
                dendro_section.x_dist_end,
                bool_=False,
            )
        return out

    def _plot_dendrite_hist(self, ax, xlim, binsize=50):
        """Base method for plotting a histogram of dendrite length on an :py:class:`matplotlib.axes.Axes` object.

        Args:
            ax (:py:class:`matplotlib.axes.Axes`): The matplotlib axes object.
            xlim (tuple): The x-axis limits.
            binsize (float): The size of the bins. Default is `50`.

        Returns:
            :py:class:`matplotlib.axes.Axes`: The matplotlib axes object.
        """
        self._compute_dendrite_hist(xlim[1], binsize=binsize)
        histogram(
            (self.bins, self.dendrite_density),
            label="dendrite",
            colormap={"dendrite": "k"},
            ax=ax,
        )
        ax.set_ylabel("dendritic length / bin", color="k")
        ax.set_xlim(xlim)
        return ax

    def _compute_dendrite_hist(self, dist_end=None, binsize=50):
        """Compute the dendrite density histogram.

        Args:
            dist_end (float): The maximum soma distance. Default is `None` and the maximum soma distance is calculated.
            binsize (float): The size of the bins. Default is `50`.

        Returns:
            None: Nothing. Updates :paramref:`bins` and :paramref:`dendrite_density`.
        """
        if dist_end is None:
            dist_end = _get_max_somadistance(self.dendrogram_db)
        bins = np.arange(0, dist_end + binsize, binsize)

        dendrite_density = [
            self._get_amount_of_dendrite_in_bin(bins[lv], bins[lv + 1])
            for lv in range(len(bins) - 1)
        ]

        self.bins = bins
        self.dendrite_density = dendrite_density = np.array(dendrite_density)


class _DendrogramSynapseStatistics:
    """Compute synapse statistics for a :py:class:`~single_cell_parser.cell.Cell` object.

    Synaptic statistics include the total amount of synapses binned by soma distance, both unnormalized, as well
    as normalized by total amount of dendritic length.

    Attributes:
        dendrogram_db (list): A list of :py:class:`_DendrogramSection` objects.
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        colormap_synapses (dict): A dictionary mapping color to synapse types. The keys must match the synapse types in the dendrogram.
            Missing keys will be omitted from the visualization alltogether. Default: `None` (plot all synapses in black).
        bins (np.array): The bins of the synapse density histogram.
        synapse_density (np.array): The synapse density histogram, i.e. the amount of synapses within a range of soma distance.
        synapse_density_apical (np.array): The synapse density histogram for apical dendrites.
        synapse_density_basal (np.array): The synapse density histogram for basal dendrites.
        synapse_statistics (dict): A dictionary of synapse statistics
    """

    def __init__(self, dendrogram_db, cell, colormap_synapses=None):
        """
        Args:
            dendrogram_db (list): A list of :py:class:`_DendrogramSection` objects.
            cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
            colormap_synapses (dict): A dictionary mapping color to synapse types. The keys must match the synapse types in the dendrogram.
                Missing keys will be omitted from the visualization alltogether. Default: `None` (plot all synapses in black).
        """
        if colormap_synapses is None:
            colormap_synapses = {}
        self.dendrogram_db = dendrogram_db
        self.cell = cell
        self.bins = None
        self.synapse_density = None
        self.dendrite_density = None
        self._add_synapses()
        self._compute_synapse_statistics()
        self._compute_synapse_hist()

    def _add_synapses(self):
        """Add synapses to the dendrogram sections.

        This method iterates the :py:class:`~single_cell_parser.cell.Cell` object, extracts the relevant synapse
        information, and adds it to the corresponding :py:class:`_DendrogramSection` objects.
        It is called upon initialization.
        """
        for cell_type, synapses in self.cell.synapses.items():
            for syn in synapses:
                sec_id = syn.secID
                sec = self.cell.sections[sec_id]
                dendro_sec = _get_db_by_sec(self.dendrogram_db, sec)
                x = sec.L * syn.x + dendro_sec.x_dist_start
                dendro_sec._add_synapse(label=cell_type, x=x)

    def get_number_of_synapses_in_bin(
        self, min_, max_, select=["Dendrite", "ApicalDendrite"], label=None
    ):
        """Get the number of synapses in a certain bin of soma distance.

        Args:
            min\_ (float): The minimum soma distance.
            max\_ (float): The maximum soma distance.
            select (list): A list of labels to select. Default is `["Dendrite", "ApicalDendrite"]`.
            label (str): The label of the synapse. Default is `None`.

        Returns:
            int: The number of synapses in the bin.
        """
        out = 0
        for dendro_section in self.dendrogram_db:
            if not dendro_section.sec.label in select:
                continue
            for label in list(dendro_section.synapses.keys()):
                for syn in dendro_section.synapses[label]:
                    if min_ <= syn < max_:
                        out += 1
        return out

    def _compute_synapse_hist(self, binsize=50):
        """Compute the synapse density histogram.

        Args:
            dist_end (float): The maximum soma distance. Default is `None` and the maximum soma distance is calculated.
            binsize (float): The size of the bins. Default is `50`.

        Returns:
            None: Nothing. Updates :paramref:`bins`, :paramref:`synapse_density`, :paramref:`synapse_density_apical`, and :paramref:`synapse_density_basal`.
        """
        dist_end = _get_max_somadistance(self.dendrogram_db)
        bins = np.arange(0, dist_end + binsize, binsize)

        synapse_density = [
            self.get_number_of_synapses_in_bin(bins[lv], bins[lv + 1])
            for lv in range(len(bins) - 1)
        ]
        synapse_density_apical = [
            self.get_number_of_synapses_in_bin(
                bins[lv], bins[lv + 1], select=["ApicalDendrite"]
            )
            for lv in range(len(bins) - 1)
        ]
        synapse_density_basal = [
            self.get_number_of_synapses_in_bin(
                bins[lv], bins[lv + 1], select=["Dendrite"]
            )
            for lv in range(len(bins) - 1)
        ]

        self.bins = bins
        self.synapse_density = synapse_density = np.array(synapse_density)
        self.synapse_density_apical = synapse_density_apical = np.array(
            synapse_density_apical
        )
        self.synapse_density_basal = synapse_density_basal = np.array(
            synapse_density_basal
        )

    def _compute_synapse_statistics(self):
        """Compute the synapse statistics.

        This method calculates the total amount of synapses in the dendrogram per synapse type.
        While plotting per synapse type is supported, the default behavior is to plot all synapses in black.

        Returns:
            None: Nothing. Updates :paramref:`synapse_statistics`.
        """
        self.synapse_statistics = {}
        for dendro_section in self.dendrogram_db:
            for label in dendro_section.synapses:
                if label not in self.synapse_statistics:
                    self.synapse_statistics[label] = []
                self.synapse_statistics[label].extend(dendro_section.synapses[label])

    def _plot_synapse_density_hist(self, ax, xlim, binsize=50):
        """Plot the synapse density histogram on an :py:class:`matplotlib.axes.Axes` object.

        If no colormap is provided during initialization, all synapses are plotted in red.
        If a colormap is provided, the synapses are plotted in the respective color.

        Attention:
            If a colormap is provided, but does not contain all synapse types as they appear in
            :paramref:`~single_cell_parser.cell.Cell.synapses`, the missing synapse types are omitted from the plot.

        Args:
            ax (:py:class:`matplotlib.axes.Axes`): The matplotlib axes object.
            xlim (tuple): The x-axis limits.
            binsize (float): The size of the bins. Default is `50`.

        Returns:
            :py:class:`matplotlib.axes.Axes`: The matplotlib axes object.
        """
        self._compute_synapse_hist(xlim[1], binsize=binsize)
        if self.colormap_synapses is None:
            # Plot all
            self.colormap_synapses = {"total": "r"}
            histogram(
                (self.bins, self.synapse_density),
                label="total",
                colormap={"total": "r"},
                ax=ax,
            )
        else:
            # plot per label
            for label in self.colormap_synapses:
                histogram(
                    (self.bins, self.synapse_statistics[label]),
                    label=label,
                    colormap=self.colormap_synapses,
                    ax=ax,
                )
        ax.legend()
        ax.set_xlim(xlim)
        ax.set_ylabel("# syn / micron dendritic length", color="k")
        return ax

    def _plot_synapse_hist(self, ax, dendrite_density):
        """Plot the synapse histogram on an :py:class:`matplotlib.Axes` object.

        Args:
            ax (:py:class:`matplotlib.Axes`): The matplotlib axes object.
            dendrite_density (np.array): The dendrite density histogram, containing the total amound of dendritic length in a certain bin of soma distance.

        Returns:
            :py:class:`matplotlib.Axes`: The matplotlib axes object.
        """
        histogram(
            (self.bins, self.synapse_density / dendrite_density),
            label="total",
            colormap={"total": "k"},
            ax=ax,
        )
        ax.legend()
        ax.set_ylabel("# syn / micron dendritic length", color="k")

    def _plot_synapses_dendrogram_overlay(self, ax):
        """Plot the synapses on the dendrogram.

        Given an :py:class:`~matplotlib.axes.Axes` object containing a dendrogram plot,
        this method plots the synapses on the dendrogram as an overlay.

        Args:
            ax (:py:class:`matplotlib.Axes`): The matplotlib axes object.

        Returns:
            :py:class:`matplotlib.Axes`: The matplotlib axes object.
        """
        syn_lines = []
        syn_colors = []
        for dendro_section in self.dendrogram_db:
            sec_id = dendro_section.sec_id
            for syntype in dendro_section.synapses:
                for syn in dendro_section.synapses[syntype]:
                    syn_lines.append(
                        (
                            [syn, sec_id + 0.5],
                            [syn, sec_id - 0.5],
                        )
                    )
                    syn_colors.append(self.colormap_synapses.get(syntype, "k"))
        syn_line_segments = LineCollection(syn_lines, colors=syn_colors, linewidths=0.3)
        ax.add_collection(syn_line_segments)
        return ax

    def plot(self, ax=None):
        """Plot the synapse statistics

        Plots out a histogram of the total amount of synapses per bin of soma distance.

        Args:
            ax (:py:class:`matplotlib.axes.Axes`): The matplotlib axes object. Default is `None` and a new figure is created.

        Returns:
            :py:class:`matplotlib.axes.Axes`: The matplotlib axes object.
        """
        if ax is None:
            fig = plt.figure(figsize=(8, 10), dpi=200)
            ax = fig.add_subplot(211)

        ax = self._plot_synapse_hist(ax)
        return fig


class DendrogramStatistics(Dendrogram):
    """Plot dendrogram statistics.

    This class creates a composite plot of a dendrogram, as well as dendritic length and synapse count statistics.
    These statistics include:

    - The total amount of dendritic length in a certain bin of soma distance.
    - The total amount of synapses in a certain bin of soma distance.
    - The total amount of synapses per micron dendritic length.

    Example::

        >>> d = DendrogramStatistics(cell)
        >>> fig = d.plot()
        >>> plt.show()

    .. figure:: ../../../_static/_images/dendrogram_statistics.png

    Attributes:
        dendrogram (:py:class:`Dendrogram`): The dendrogram object.
        dend_statistics (:py:class:`_DendrogramDendriteStatistics`): The dendrite statistics object.
        syn_statistics (:py:class:`_DendrogramSynapseStatistics`): The synapse statistics object.
    """

    def __init__(self, cell):
        """
        Args:
            cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        """
        self.dendrogram = Dendrogram(cell)
        self.dend_statistics = _DendrogramDendriteStatistics(
            self.dendrogram.dendrogram_db
        )
        self.syn_statistics = _DendrogramSynapseStatistics(
            self.dendrogram.dendrogram_db, cell=cell
        )

    def plot(self, figsize=None, colormap_synapses=None):
        """Plot the dendrogram statistics.

        Args:
            figsize (tuple): The figure size. Default is `None`.
            colormap_synapses (dict): A dictionary mapping color to synapse types. The keys must match the synapse types in the dendrogram.
                Missing keys will be omitted from the visualization alltogether. Default: `None` (plot all synapses in black).

        Returns:
            :py:class:`matplotlib.figure.Figure`: The matplotlib figure object.
        """
        self.syn_statistics.colormap_synapses = colormap_synapses
        if figsize is None:
            figsize = (8, 10)
        fig = plt.figure(figsize=figsize)
        gs = gridspec.GridSpec(3, 1, height_ratios=[2, 1, 1])
        ax = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1])
        ax3 = fig.add_subplot(gs[2])

        ax = self.dendrogram._plot_dendrogram(ax)
        xlim = ax.get_xlim()
        ax2 = self.dend_statistics._plot_dendrite_hist(ax2, xlim=xlim)
        ax2_2 = ax2.twinx()
        ax2_2 = self.syn_statistics._plot_synapse_density_hist(ax2_2, xlim=xlim)
        ax3 = self.syn_statistics._plot_synapse_hist(
            ax3, dendrite_density=self.dend_statistics.dendrite_density
        )
        ax = self.syn_statistics._plot_synapses_dendrogram_overlay(ax)
        return fig
