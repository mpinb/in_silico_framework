from biophysics_fitting import get_main_bifurcation_section
import pandas as pd
from distributed import Client, LocalCluster
from matplotlib import colors as mcolors
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mpl_toolkits.mplot3d.art3d import Line3DCollection
import numpy as np
import shutil
from visualize.vtk import write_vtk_skeleton_file
import os, dask, time, six, socket, barrel_cortex, warnings
from .utils import write_video_from_images, write_gif_from_images, display_animation_from_images, draw_arrow
if six.PY3:
    from scipy.spatial.transform import Rotation
else:
    # let ImportWarnings show up when importing this module through Interface
    warnings.filterwarnings("default", category=ImportWarning, module=__name__)
    warnings.warn(
        "Scipy version is too old to import spatial.transform.Rotation. Cell alignment will not work."
    )
    warnings.warn(
        "Interactive visualizations only work on Py3. Dash and plotly are not compatible with the Py2 version of ISF."
    )
import logging
logger = logging.getLogger("ISF").getChild(__name__)
# For interactive visualizations
try:
    from dash import Dash, dcc, html, Input, Output
    from dash import callback_context as ctx
    import plotly.offline as py
    import plotly.io as pio
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError as e:
    logger.warning(e)


class CMVDataParser:
    def __init__(
        self, 
        cell, 
        align_trunk=True, 
        t_start=None, t_stop=None, t_step=None):
        """
        Given a Cell object, this class initializes an object that is easier to work with for visualization purposes
        """
        # ---------------------------------------------------------------
        # Cell object
        self.cell = cell
        """The Cell object"""

        # ---------------------------------------------------------------
        # Morphology attributes
        # Gather the necessary information to plot the cell morphology.
        # This info is always necessary to plot the cell.

        self.line_pairs = []  # initialised below
        """Pairs of point indices that define a line, i.e. some cell segment"""
        self.soma = self.cell.soma
        self.soma_center = np.mean(self.soma.pts, axis=0)
        """Center of the soma of the original cell object, unaligned with z-axis."""
        self.parents = {}
        """Maps sections to their parents. self.parents[10] returns the parent of section 10."""
        self._morphology_unconnected = self.morphology = None
        """A pd.DataFrame containing point information, diameter and section ID"""
        self._morphology_connected = None
        """A pd.DataFrame containing point information, diameter and section ID with duplicated points for branchpoints for connections between sections.
        This is the morphology dataframe that's most often used. Only the interactive visualizer plots out self.morphology."""
        self.sections = None
        """A set of section indices"""
        self.n_sections = None
        self._calc_morphology(cell)  # a pandas DataFrame
        self.rotation_with_zaxis = None
        """Rotation object that defines the transformation between the cell trunk and the z-axis"""
        if align_trunk:
            self._align_trunk_with_z_axis(cell)

        # -------------------------------
        # colors and color scales. default colorscale is for membrane voltage
        self.background_color = (1, 1, 1, 1)  # white
        self.vmin, self.vmax = None, None  # legend bounds
        self.norm = None
        self.cmap = plt.get_cmap("jet")  # default
        self.scalar_mappable = None

        # ---------------------------------------------------------------
        # Simulation-related parameters
        # These only get initialised when the cell object actually contains simulation data.
        # This info is not necessary to plot the cell morphology, but some more advanced methods need this information

        self.simulation_times = None
        """Time points of the simulation"""
        self.time_offset = None
        """Time offset w.r.t. simulation start. useful if '0 ms' is supposed to refer to stimulus time"""
        self.t_start = t_start
        """Time point where we want to start visualising.
        By default, this gets initialised to the start of the simulation."""
        self.t_stop = t_stop
        """Time point where the visualisation of the simulation stops.
        By default, this gets initialised to the end of the simulation."""
        self.dt = None
        """Time interval of the simulation"""
        # TODO: add support for variable timestep
        self.t_step = t_step
        """Time interval for visualisation. Does not have to equal the simulation time interval.
        By default, the simulation is chopped to the specified t_begin and t_stop, and evenly divided in 10 timesteps."""
        self.times_to_show = None
        """An array of time points to visualize. Gets calculated from :paramref:self.t_start, :paramref:self.t_stop and :paramref:self.t_step"""
        recordvars_all_sections = [list(sec.recordVars.keys()) for sec in cell.sections]
        self.possible_scalars = set([e for recordvars_this_section in recordvars_all_sections for e in recordvars_this_section])
        """Accepted keywords for scalar data other than membrane voltage."""

        self.voltage_timeseries = None
        """List contaning the voltage of the cell during a timeseries. Each element corresponds to a time point.
        Each element of the list contains n elements, being n the number of points of the cell morphology. 
        Hence, the value of each element is the voltage at each point of the cell morphology.
        None means it has no simulation data. Empty list means it has simulation data that has not been initialised yet."""

        self.synapses_timeseries = None
        """List containing the synapse activations during a timeseries (Similarly to voltage_timeseries). 
        Each element corresponds to a time point. Each element is a dictionary where each key is the type of
        input population and the value is the list of active synapses for that type of population at that time point. 
        The list contains the 3d coordinates where each active synapse is located.
        None means it has no simulation data. Empty list means it has simulation data that has not been initialised yet."""

        self.ion_dynamics_timeseries = None
        """List containing the ion dynamics during a timeseries (Similarly to voltage_timeseries). 
        Each element is a list corresponding to 1 timepoint, containing per-point info on the ion channel state or ion concentration.
        None means it has no simulation data. Empty list means it has simulation data that has not been initialised yet.
        """

        self.time_show_syn_activ = 2  # ms
        """Time in the simulation during which a synapse activation is shown during the visualization"""

        if self._has_simulation_data():
            self._init_simulation_data()

    def _has_simulation_data(self):
        """
        Test if the cell object has been simulated by checking if it has voltage data
        """
        return len(self.soma.recVList[0]) > 0

    def _init_simulation_data(self):
        """
        Initializes the variables associated with simulation data. Does not fill these variables until they actually need to be calculated.
        """
        # Time points of the simulation
        self.simulation_times = np.array(self.cell.tVec)
        # Time offset w.r.t. simulation start. useful if '0 ms' is supposed to refer to stimulus time
        self.time_offset = 0
        # Time points we want to visualize (values by default)
        self.t_start = self.simulation_times[0] if self.t_start is None else self.t_start
        self.dt = np.median(np.diff(self.simulation_times))  # median time interval
        if self.t_step is None:
            self.t_step = .1*(self.simulation_times[-1] - self.simulation_times[0]) if self.t_step is None else self.t_step
            logger.warning("No t_step provided. Setting t_step to default 1/10th of the total simulation time ~= {:.2f}".format(self.t_step))
        self.t_stop = self.simulation_times[-1] - self.simulation_times[-1] % self.t_step if self.t_stop is None else self.t_stop
        self.times_to_show = np.empty(0)
        # initialise time range to visualise
        self._update_times_to_show(self.t_start, self.t_stop, self.t_step)
        """List contaning the voltage of the cell during a timeseries. Each element corresponds to a time point.
        Each element of the list contains n elements, being n the number of points of the cell morphology. 
        Hence, the value of each element is the voltage at each point of the cell morphology."""
        self.voltage_timeseries = []
        """List containing the synapse activations during a timeseries (Similarly to voltage_timeseries). 
        Each element corresponds to a time point. Each element is a dictionary where each key is the type of
        input population and the value is the list of active synapses for that type of population at that time point. 
        The list contains the 3d coordinates where each active synapse is located."""
        self.synapses_timeseries = []
        self.ion_dynamics_timeseries = {}

        # Time in the simulation during which a synapse activation is shown during the visualization
        self.time_show_syn_activ = 2  # ms

    def _align_trunk_with_z_axis(self, cell):
        """
        Calculates the polar angle between the trunk and z-axis (zenith).
        Anchors the soma to (0, 0, 0) and aligns the trunk to the z-axis.

        Args:

        Returns:
        Nothing
        """

        assert len(self._morphology_unconnected) > 0, "No morphology initialised yet"
        # the bifurcation sections is the entire section: can be quite large
        # take last point, i.e. furthest from soma
        bifurcation = get_main_bifurcation_section(cell).pts[-1]
        soma_bif_vector = bifurcation - self.soma_center
        soma_bif_vector /= np.linalg.norm(soma_bif_vector)
        # angle with z-axis
        zenith = np.arccos(np.dot([0, 0, 1], soma_bif_vector))
        xy_proj = [soma_bif_vector[0], soma_bif_vector[1], 0]
        xy_proj /= np.linalg.norm(xy_proj)
        # create vector to rotate about
        xy_proj_orth = [xy_proj[1], -xy_proj[0], 0]
        # rotation towards z-axis as rotation vector
        # as rotation vector: direction is axis to rotate about, norm is angle of rotation
        rot_vec = [e * zenith for e in xy_proj_orth]
        rotation = Rotation.from_rotvec(rot_vec)

        # Anchor soma to (0, 0, 0) and rotate trunk to align with z-axis
        self._morphology_connected[['x', 'y', 'z']] = rotation.apply([
            e - self.soma_center
            for e in self._morphology_connected[['x', 'y', 'z']].values
        ])

        self.rotation_with_zaxis = rotation

    def _calc_morphology(self, cell):
        '''
        Retrieve cell MORPHOLOGY from cell object.
        Fills the self.morphology attribute
        '''
        t1 = time.time()

        points = []
        for sec_n, sec in enumerate(cell.sections):
            if sec.label == 'Soma':
                n_segments = len([seg for seg in sec])
                for i, pt in enumerate(sec.pts):
                    seg_n = int(n_segments * i / len(sec.pts))
                    x, y, z = pt
                    d = sec.diamList[i]
                    points.append([x, y, z, d, sec_n, seg_n])
                # print('adding soma')
                # print(sec_n)
                # x, y, z = self.soma_center
                # # soma size
                # mn, mx = np.min(cell.soma.pts, axis=0), np.max(cell.soma.pts,
                #                                                axis=0)
                # d_range = [mx_ - mn_ for mx_, mn_ in zip(mx, mn)]
                # d = max(d_range)
                # points.append([x, y, z, d, sec_n, 0])
            elif sec.label in ['AIS', 'Myelin']:
                continue
            else:
                self.parents[sec_n] = cell.sections.index(sec.parent)
                # Points within the same section
                xs_in_sec = [seg.x for seg in sec]
                n_segments = len([seg for seg in sec])
                for i, pt in enumerate(sec.pts):
                    seg_n = int(n_segments * i / len(sec.pts))
                    x, y, z = pt
                    d = sec.diamList[i]
                    points.append([x, y, z, d, sec_n, seg_n])

        self._morphology_connected = pd.DataFrame(
            points, 
            columns=['x', 'y', 'z', 'diameter', 'sec_n', 'seg_n'])
        self._morphology_connected['sec_n'] = self._morphology_connected['sec_n'].astype(int)
        self._morphology_connected['seg_n'] = self._morphology_connected['seg_n'].astype(int)
        t2 = time.time()
        logger.info('Initialised simulation data in {} seconds'.format(
            np.around(t2 - t1, 2)))
        
        self.sections = self._morphology_connected['sec_n'].unique()
        self.n_sections = len(self.sections)
        for sec in self.sections[1:]:
            parent_sec = self.parents[sec]
            parent_point = self._morphology_connected[self._morphology_connected['sec_n'] == parent_sec].iloc[[-1]]
            parent_point["sec_n"] = sec
            self._morphology_connected = pd.concat([parent_point, self._morphology_connected])
        # the first ``n_sections`` points are now the branch points
        # indexing the df by section number will always begin with the branch point, i.e. first point of the section
    
        self._morphology_unconnected = self.morphology = self._morphology_connected[self.n_sections-1:]
    
    def _get_voltages_at_timepoint(self, time_point):
        '''
        Retrieves the VOLTAGE along the whole cell morphology from cell object at a particular time point.
        Each voltage is defined per section in the morphology. 
        Note that the array of data per section each time starts with the last point of its parent section.

        Fetches this voltage from the original cell object.

        Args:
         - time_point: time point from which we want to gather the voltage
        '''
        n_sim_point = np.argmin(np.abs(self.simulation_times - time_point))
        voltage_points = [[self.soma.recVList[0][n_sim_point]] * len(self.morphology[self.morphology['sec_n'] == 0])]
        for _, sec in enumerate([sec for sec in self.cell.sections if sec.label not in ("Soma", "Myelin", "AIS")]):
            n_segs = len([seg for seg in sec])
            n_pts = len(sec.pts)
            # First point of this section is last point of prev section
            voltage_points_this_section = [sec.parent.recVList[-1][n_sim_point]]
            for n, _ in enumerate(sec.pts):
                seg_n = int(n* n_segs / (n_pts-1)) if n != n_pts-1 else n_segs-1
                voltage_points_this_section.append(sec.recVList[seg_n][n_sim_point])
            voltage_points.append(voltage_points_this_section)
        return voltage_points

    def _data_per_section_to_data_per_point(self, data_per_section):
        d_per_point = data_per_section[0]
        for data in data_per_section[1:]:
            d_per_point.extend(data[1:])
        return d_per_point
    
    def _get_ion_dynamics_at_timepoint(self, time_point, ion_keyword):
        '''
        Retrieves the ion dynamics along the whole cell morphology from cell object at a particular time point.
        Note that the array of data per section each time starts with the last point of its parent section.

        Args:
         - time_point: time point from which we want to gather the voltage
        '''
        n_sim_point = np.argmin(np.abs(self.simulation_times - time_point))
        ion_points = [[self.soma.recordVars[ion_keyword][0][n_sim_point] or np.nan]]
        for sec_n, sec in enumerate([sec for sec in self.cell.sections if sec.label not in ("Soma", "Myelin", "AIS")]):
            n_segs = len([seg for seg in sec])
            n_pts = len(sec.pts)
            if len(sec.recordVars[ion_keyword]) > 0:
                ion_points_this_section = [sec.parent.recordVars[ion_keyword][-1][n_sim_point]]
            else:
                ion_points_this_section = [np.nan]
            for n, pt in enumerate(sec.pts):
                seg_n = int(n* n_segs / (n_pts-1)) if n != n_pts-1 else n_segs-1
                if len(sec.recordVars[ion_keyword]) > 0:
                    ion_points_this_section.append(sec.recordVars[ion_keyword][seg_n][n_sim_point])
            ion_points.append(ion_points_this_section)
        return ion_points
    
    def _calc_voltage_timeseries(self):
        '''
        Retrieves VOLTAGE along the whole cell body during a set of time points (specified in self.times_to_show).
        Fills the self.voltage_timeseries attribute.
        Only does so when it has not been computed yet.

        Returns:
            Nothing. Updates the self.timeseries_voltage attribute
        '''
        self._update_times_to_show(self.t_start, self.t_stop, self.t_step)
        if len(self.voltage_timeseries) != 0:
            return  # We have already retrieved the voltage timeseries

        logger.info("Fetching voltage timeseries...")
        t1 = time.time()
        for time_point in self.times_to_show:  # For each frame of the video/animation
            voltage = self._get_voltages_at_timepoint(time_point)
            self.voltage_timeseries.append(voltage)
        t2 = time.time()
        logger.info('Voltage retrieval runtime (s): ' + str(np.around(t2 - t1, 2)))
        
        # Update cmap if necessary
        self.set_cmap(
            self.cmap, 
            vmin=min(min([min(e) for e in self.voltage_timeseries])) if self.vmin is None else self.vmin, 
            vmax=max(max([max(e) for e in self.voltage_timeseries])) if self.vmax is None else self.vmax)

    def _calc_ion_dynamics_timeseries(self, ion_keyword):
        '''
        Retrieves ion dynamics info along the whole cell body during a set of time points (specified in self.times_to_show).
        Fills the self.ion_dynamics attribute.
        Only does so when it has not been computed yet.

        Returns:
            Nothing. Updates the self.timeseries_voltage attribute
        '''
        self._update_times_to_show(self.t_start, self.t_stop, self.t_step)
        assert ion_keyword in self.possible_scalars, \
            "Ion keyword \"{}\" not recognised. Possible keywords are: {}".format(ion_keyword, self.possible_scalars)
        assert any([ion_keyword in sec.recordVars.keys() for sec in self.cell.sections]), \
            "No sections found with ion dynamics for ion keyword " + ion_keyword

        if ion_keyword in self.ion_dynamics_timeseries.keys():
            return  # We have already calculated the ion_dynamics_timeseries
        else:
            self.ion_dynamics_timeseries[ion_keyword] = []

        logger.info("Fetching ion dynamics timeseries...")
        t1 = time.time()
        for time_point in self.times_to_show:  # For each frame of the video/animation
            ion_dynamics = self._get_ion_dynamics_at_timepoint(
                time_point, ion_keyword)
            self.ion_dynamics_timeseries[ion_keyword].append(ion_dynamics)
        t2 = time.time()
        logger.info('Ion dynamics retrieval runtime (s): ' +
              str(np.around(t2 - t1, 2)))
        
        # Update cmap if necessary
        self.set_cmap(
            self.cmap, 
            vmin=min(min([min(e) for e in self.ion_dynamics_timeseries[ion_keyword]])) if self.vmin is None else self.vmin, 
            vmax=max(max([max(e) for e in self.ion_dynamics_timeseries[ion_keyword]])) if self.vmax is None else self.vmax)

    def _get_synapses_at_timepoint(self, time_point):
        '''
        Retrieves the SYNAPSE ACTIVATIONS at a particular time point.

        Args:
         - time_point: time point from which we want to gather the synapse activations
        '''

        synapses = {}

        for population in self.cell.synapses.keys():
            for synapse in self.cell.synapses[population]:
                if synapse.preCell is None:
                    continue
                for spikeTime in synapse.preCell.spikeTimes:
                    if time_point <= spikeTime < time_point + self.time_show_syn_activ:
                        population_name = self.synapse_group_function(
                            population)
                        pt = synapse.coordinates
                        if self.rotation_with_zaxis is not None:  # no alignment with z-axis
                            pt = self.rotation_with_zaxis.apply(
                                synapse.coordinates - self.soma_center)
                        if not population_name in synapses:
                            synapses[population_name] = []
                        synapses[population_name].append(pt)
        return synapses

    def _calc_synapses_timeseries(self):
        '''
        Retrieves the SYNAPSE ACTIVATIONS during a set of time points (specified in self.time).
        Fills the self.synapses_timeseries attribute.
        '''
        if len(self.synapses_timeseries) != 0:
            return  # We have already retrieved the synapses timeseries

        logger.info("Fetching synapse timeseries...")
        t1 = time.time()
        for time_point in self.times_to_show:  # For each frame of the video/animation
            synapses = self._get_synapses_at_timepoint(time_point)
            self.synapses_timeseries.append(synapses)
        t2 = time.time()
        logger.info('Synapses retrieval runtime (s): ' + str(np.around(t2 - t1, 2)))
        if all([e == {} for e in self.synapses_timeseries]):
            logger.warning("No synaptic activity found in simulation")

    def _get_timeseries_minmax(self, timeseries):
        """
        Timeseries have two axes: time, section_id. Each timeseries[time][section_id] shows values for all points in that section at that time.
        Getting minmax of nested lists can be annoying, hence this method.
        
        Returns min and max for some timeseries across all timepoints and sections.
        """
        mn = 1e10
        mx = -1e10
        for data_at_time in timeseries:
            for data_at_section in data_at_time:
                mn = np.nanmin((np.nanmin(data_at_section), mn))
                mx = np.nanmax((np.nanmax(data_at_section), mx))
        return mn, mx
    
    def _update_times_to_show(self, t_start=None, t_stop=None, t_step=None):
        """Checks if the specified time range equals the previously defined one. If not, updates the time range.
        If all arguments are None, does nothing. Useful for defining default time range

        Args:
            t_start (float): start time
            t_stop (float): end time
            t_step (float): time interval
        """
        if not all([e is None for e in (t_start, t_stop, t_step)]):
            # At least one of the time range parameters needs to be updated
            if t_start is not None:
                assert t_start >= self.simulation_times[
                    0], "Specified t_start is earlier than the simulation time of {} ms".format(
                        self.simulation_times[0])
                assert t_start <= self.simulation_times[
                    -1], "Specified t_start is later than the simulation end time of {} ms".format(
                        self.simulation_times[-1])
                self.t_start = t_start  # update start if necessary
            # check if closed interval is possible
            if t_stop is not None:
                assert t_stop <= self.simulation_times[
                    -1], "Specified t_stop exceeds the simulation time of {} ms".format(
                        self.simulation_times[-1])
                self.t_stop = t_stop
            if t_step is not None:
                self.t_step = t_step

            new_time = np.arange(self.t_start, self.t_stop + self.t_step,
                                 self.t_step)
            if len(self.times_to_show
                  ) != 0:  # there were previously defined times
                if len(self.times_to_show) == len(new_time):
                    # there are timepoints that are newly defined
                    if (self.times_to_show != new_time).any():
                        self.ion_dynamics_timeseries = {}
                        self.voltage_timeseries = []
                        self.synapses_timeseries = []
                else:  # there were no times previously defined
                    self.ion_dynamics_timeseries = {}
                    self.voltage_timeseries = []
                    self.synapses_timeseries = []
            self.times_to_show = new_time

    def _calc_scalar_data_from_keyword(
        self, 
        keyword, 
        time_point,
        return_as_color=False,
        color_dict={}):
        """
        Returns a data array based on some keyword.
        If ``return_as_color``is True (default), the returned array is a map from the input keyword to a color
        Otherwise, it is the raw data, not mapped to a colorscale. Which data is returned (mapped to colors or not)
        depends on the keyword (case-insensitive):
        - ("voltage", "vm"): voltage
        - Some rangeVar: ion dynamics. See self.available_scalars for possibilities.
        - regular string: will try to convert to amatplotlib accepted color string
        """

        # -------------- Fixed colors
        if keyword.lower() in ("dendrites", "dendritic group"):
            if not return_as_color:
                raise NotImplementedError("Dendritic groups are always colors")
            if not color_dict:
                raise ValueError("Please provide a dictionary mapping section labels to colors")
            return_data = []
            for sec in self.sections:
                if sec.label in color_dict:
                    color = color_dict[sec.label]
                    return_data.append(color)
                else:
                    return_data.append('grey')
            return return_data
        
        elif keyword in list(mcolors.BASE_COLORS) + list(mcolors.TABLEAU_COLORS) + list(mcolors.CSS4_COLORS) + list(mcolors.XKCD_COLORS):
            # These colors are defined per section, not per segment.
            return_data = [[keyword]]
            for sec in self.cell.sections:
                if not sec.label in ("AIS", "Myelin", "Soma"):
                    return_data.append([keyword for _ in sec.pts])
            return return_data

        # -------------- Keyword colors       
        elif keyword.lower() in ("voltage", "vm"):
            self._calc_voltage_timeseries()  # Only happens if necessary
            data_per_section = self._get_voltages_at_timepoint(time_point)
        
        elif keyword in self.possible_scalars:
            self._calc_ion_dynamics_timeseries(keyword)  # Only happens if necessary
            data_per_section = self._get_ion_dynamics_at_timepoint(time_point, keyword)

        else:
            raise ValueError("Color keyword not recognized. Available options are: \"voltage\", \"vm\", \"dendrites\", \"dendritic group\", a color from self.possible_scalars, or a color from matplotlib.colors")
        return_data = self._get_color_per_section(data_per_section) if return_as_color else data_per_section
        return return_data
    
    def _keyword_is_scalar_data(self, keyword):
        if isinstance(keyword, str):
            return keyword in ("voltage", "vm", "synapses", "synapse", "dendrites", "dendritic_group") + tuple(self.possible_scalars)
        return True  # if not string, should be scalar data
    
    def _get_color_per_section(
        self, 
        array, 
        nan_color="#f0f0f0"):
        """
        Given an array of scalar values of length n_points, bin them per section and assign a color according to self.scalar_mappable.
        If there is no data for a given point, it will be
        """
        color_per_section = [self.scalar_mappable.to_rgba(data) for data in array]
        return color_per_section
    
    def scale_diameter(self, scale_func):
        """
        Scale the diameter of the visualization with a scaling function.
        ``scale_func`` should transform an array to an array of equal length.
        To set a fixed diameter rather than scaling, pass `lambda x: fixed_d`

        Args:
            scale_func: method to scale the diameters with. Must accept an array and return an array. This will be passed to `pd.DataFrame.apply()`

        Returns:
            None: Nothing. 
        """
        self._morphology_connected['diameter'] = self._morphology_connected['diameter'].apply(scale_func)
        assert self._morphology_unconnected['diameter'] == self.morphology['diameter'] == self._morphology_connected[self.n_sections-1:]['diameter']
    
    def set_cmap(
        self, 
        cmap=None, 
        vmin=None, 
        vmax=None):
        self.vmin = vmin if vmin is not None else self.vmin
        self.vmax = vmax if vmin is not None else self.vmax
        self.norm = mpl.colors.Normalize(self.vmin, self.vmax)
        self.cmap = cmap if cmap is not None else self.cmap
        self.scalar_mappable = mpl.cm.ScalarMappable(norm=self.norm, cmap=self.cmap)


class CellMorphologyVisualizer(CMVDataParser):
    """
    This class initializes from a cell object and extracts relevant Cell data to a format that lends itself easier to plotting.
    It contains useful methods for: 
        1. plotting a cell morphology
        2. the voltage along its body
        3. its synaptic inputs.
    This can be visualized in static images or as time series (videos, gif, animation, interactive window).
    It relies mostly on Matplotlib to do so.

    The relevant cell information can also be exported to .vtk format for further visualization or interaction.
    No explicit VTK dependency is needed for this; it simply writes it out as a .txt file.
    """

    def __init__(
        self, 
        cell, 
        align_trunk=True, 
        t_start=None, t_stop=None, t_step=None):
        """
        Given a Cell object, this class initializes an object that is easier to work with.
        
        Args:
            cell (:class:`~single_cell_parser.cell.Cell`): Cell object
            align_trunk (bool): Whether or not to align the cell trunk with the z-axis.
            t_start (float): start time point of our time series visualization
            t_stop (float): last time point of our time series visualization
            t_step (float): time between the different time points of our visualization
            
        Attributes:
            camera_position (dict): 
                Camera angles and distance for matplotlib 3D visualizations.
                Possible keys: 'azim', 'dist', 'elev', 'roll'
                See also: https://matplotlib.org/stable/api/toolkits/mplot3d/view_angles.html
            neuron_rotation (float): 
                Amount of degrees the azimuth increases per frame in a timeseries visualization.
            dpi (int): 
                Image quality
                Default: 72
            show_synapses (bool): 
                Whether or not to visualize the location of synapses onto the cell.
            synapse_legend (bool): 
                whether the synapse activations legend should appear in the plot
            highlight_arrow_kwargs (dict): 
                Additional arguments for the arrow. 
                See available kwargs on https://matplotlib.org/3.1.1/api/_as_gen/matplotlib.patches.Arrow.html#matplotlib.patches.Arrow
            synapse_group_function (callable): 
                Method to group synapse types. 
                Must accept a name (str) as argument, and return a group name (str) as output.
                Default: `lambda x: x`
            population_to_color_dict (dict)
                Dictionary to map synapse group names (str) to colors
                Must contain the same keys as self.cell.synapses.keys() after being passed through self.synapse_group_function
                default: {}
            
        Note:
            :paramref:`align_trunk` assumes the cell has a trunk, which is defined as the dendrite between the soma
            and the main bifurcation section: :meth:`~biophysics_fitting.get_main_bifurcation_section`.
        """
        super().__init__(cell, align_trunk, t_start, t_stop, t_step)
        # ---------------------------------------------------------------
        # Visualization attributes
        self.camera_position = {'azim': 0, 'dist': 10, 'elev': 30, 'roll': 0}
        self.neuron_rotation = 0.5
        self.dpi = 72
        self.show_synapses = True
        self.synapse_legend = True
        self.legend = True
        self.highlight_arrow_kwargs = None        
        self.synapse_group_function = lambda x: x # barrel_cortex.synapse_group_function_HZpaper
        self.population_to_color_dict = {}  # barrel_cortex.color_cellTypeColorMapHotZone    

    def _write_png_timeseries(
            self, 
            path,
            overwrite_frames=False,
            color="grey",
            show_synapses=False,
            show_legend=False,
            client=None, 
            highlight_section=None, 
            highlight_x=None
        ):
        '''
        Creates a list of images where a neuron morphology color-coded with voltage together with synapse activations are
        shown for a set of time points. These images will then be used for a time-series visualization (video/gif/animation)
        and in each image the neuron rotates a bit (3 degrees) over its axis.

        The parameters :param self.t_start:, :param self.t_stop: and :param self.t_step: will define the :param self.times_to_show: attribute

        Args:
            - t_start: start time point of our time series visualization
            - t_stop: last time point of our time series visualization
            - t_step: time between the different time points of our visualization
            - path: path were the images should be stored
            - client: dask client for parallelization
        '''
        if os.path.exists(path):
            if os.listdir(path) and not overwrite_frames:
                logger.info(
                    'Images already generated, they will not be generated again. Please, change the path name, delete the current one, or set overwrite_frames to True.'
                )
                return
            elif overwrite_frames:
                shutil.rmtree(path)
                os.mkdir(path)
        else:
            os.mkdir(path)

        # Gathers the voltage and synapse activations time series.
        # Then images are generated for each specified time step.
        self._update_times_to_show()
        if show_synapses:
            self._calc_synapses_timeseries()

        highlight_section_kwargs={
            'sec_n': highlight_section,
            'highlight_x': highlight_x,
            'arrow_args': self.highlight_arrow_kwargs}

        delayeds = []
        azim_ = self.camera_position['azim']

        t1 = time.time()
        maybe_scattered_df = client.scatter(self._morphology_connected, broadcast=True) if client is not None else self._morphology_connected
        if client is None:
            logger.warning("No dask client provided. Images will be generated on a single thread, which may take some time.")
            client = Client(LocalCluster(n_workers=1, threads_per_worker=1))
        legend = self.scalar_mappable if show_legend else None
        
        count = 0
        for time_point in self.times_to_show:
            color_per_section = self._calc_scalar_data_from_keyword(color, time_point, return_as_color=True)
            count += 1
            filename = os.path.join(path, '{0:0=5d}.png'.format(count))
            delayeds.append(
                dask.delayed(get_3d_plot_morphology)(
                    lookup_table=maybe_scattered_df,
                    colors=color_per_section,
                    synapses=self._get_synapses_at_timepoint(time_point) if show_synapses else {},
                    color_keyword=color,
                    time_point=time_point - self.time_offset,
                    save=filename,
                    population_to_color_dict=self.population_to_color_dict,
                    camera_position=self.camera_position,
                    legend=legend,
                    synapse_legend=show_legend and show_synapses,
                    dpi=self.dpi,
                    highlight_section_kwargs=highlight_section_kwargs,
                    plot=False,
                    return_figax=False))
            self.camera_position['azim'] += self.neuron_rotation
        self.camera_position['azim'] = azim_
        futures = client.compute(delayeds)
        client.gather(futures)
        t2 = time.time()
        logger.info('Images generation runtime (s): ' + str(np.around(t2 - t1, 2)))
    
    def plot(
        self,
        color="grey",
        show_legend=True,
        show_synapses=False,
        time_point=None,
        save='',
        highlight_section=None,
        highlight_x=None):
        '''
        Creates a python plot of the cell morphology in 3D,
        You can pass various arguments to adapt the plot, e.g. showing an overlay of the membrane voltage, or synaptic locations.

        Args:
            - color (str | [[float]]): If you want some other color overlayed on the cell morphology. 
                Options: "voltage", "vm", "synapses", "synapse", or a color string, or a nested list of colors for each section
            - legend (bool): whether the voltage legend should appear in the plot
            - show_synapses (bool): whether the synapse activations should be shown
            - time_point (int|float): time point from which we want to gather the voltage/synapses. Defaults to 0
            - save (bool): path where the plot will be saved. If it's empty it will not be saved (Default)
            - highlight_section (int): section number of the section that should be highlighted
            - highlight_x (float): x coordinate of the section that should be highlighted

        '''
        assert not (self._keyword_is_scalar_data(color) and time_point is None), "Please provide a timepoint at which to plot {}".format(color)
        if time_point is None:
            logger.info("No timepoint provided. Plotting at earliest timepoint...")
            time_point = self.times_to_show[0]
        assert time_point < self.times_to_show[-1], "Time point exceeds simulation time"
        logger.info("updating_times_to_show")
        self._update_times_to_show()
        if show_synapses:
            self._calc_synapses_timeseries()
        
        colors = self._calc_scalar_data_from_keyword(color, time_point, return_as_color=True)
        legend=None
        if show_legend and self._keyword_is_scalar_data(color):
            legend = self.scalar_mappable
        
        fig, ax = get_3d_plot_morphology(
            self._morphology_connected,
            colors=colors,
            color_keyword=color,
            synapses= self._get_synapses_at_timepoint(time_point) if show_synapses else None,
            time_point=time_point-self.time_offset if type(time_point) in (float, int) else time_point,
            camera_position=self.camera_position,
            highlight_section_kwargs={
                'sec_n': highlight_section,
                'highlight_x': highlight_x,
                'arrow_args': self.highlight_arrow_kwargs},
            legend=legend,
            synapse_legend=self.synapse_legend and show_synapses,
            dpi=self.dpi,
            save=save,
            plot=True
        )
        return fig

    def write_gif(
        self,
        images_path,
        out_name,
        color='grey',
        show_synapses=False,
        show_legend=False,
        client=None,
        t_start=None,
        t_stop=None,
        t_step=None,
        highlight_section=None,
        highlight_x=None,
        display=True,
        overwrite_frames=False,
        tpf=20):
        '''
        Creates a set of images where a neuron morphology color-coded with voltage together with synapse activations are
        shown for a set of time points. In each image the neuron rotates a bit (3 degrees) over its axis.
        These images are then put together into a gif.
        The parameters :paramref:t_start, :paramref:t_stop and :paramref:t_step will define the :paramref:self.time attribute

        Args:
            - images_path: dir where the images for the gif will be generated
            - out_path: dir where the gif will be generated + name of the gif
            - t_start: start time point of our time series visualization
            - t_stop: last time point of our time series visualization
            - t_step: time between the different time points of our visualization
            - client: dask client for parallelization
            - neuron_rotation: rotation degrees of the neuron at each frame (in azimuth)
            - time_show_syn_activ: Time in the simulation during which a synapse activation is shown during the visualization
            - vmin: min voltages colorcoded in the cell morphology
            - vmax: max voltages colorcoded in the cell morphology (the lower vmax is, the stronger the APs are observed)
            - tpf: duration of each frame in ms
        '''
        assert self._has_simulation_data()
        self._update_times_to_show(t_start, t_stop, t_step)
        if not out_name.endswith(".gif"):
            logger.warning(".gif extension not found in out_name. Adding it...")
            out_name = out_name + ".gif"
        images_path = os.path.realpath(images_path)
        self._write_png_timeseries(
            images_path,
            color=color,
            show_synapses=show_synapses,
            show_legend=show_legend,
            client=client,
            highlight_section=highlight_section,
            highlight_x=highlight_x,
            overwrite_frames=overwrite_frames)
        write_gif_from_images(images_path, out_name, interval=tpf)

    def write_video(
        self,
        images_path,
        out_path,
        overwrite_frames=False,
        color='grey',
        show_synapses=False,
        show_legend=False,
        client=None,
        highlight_section=None,
        highlight_x=None,
        quality=5,
        codec='mpeg4',
        tpf=20):
        '''
        Creates a set of images where a neuron morphology color-coded with voltage together with synapse activations are
        shown for a set of time points. In each image the neuron rotates a bit (3 degrees) over its axis.
        These images are then put together into a video.
        The parameters :paramref:t_start, :paramref:t_stop and :paramref:t_step will define the :paramref:time attribute

        Args:
            - images_path: dir where the images for the video will be generated
            - out_path: dir where the video will be generated + name of the video
            - t_start: start time point of our time series visualization
            - t_stop: last time point of our time series visualization
            - t_step: time between the different time points of our visualization
            - client: dask client for parallelization
            - neuron_rotation: rotation degrees of the neuron at each frame (in azimuth)
            - time_show_syn_activ: Time in the simulation during which a synapse activation is shown during the visualization
            - vmin: min voltages colorcoded in the cell morphology
            - vmax: max voltages colorcoded in the cell morphology (the lower vmax is, the stronger the APs are observed)
            - framerate: frames per second
            - quality
            - codec
        '''
        assert self._has_simulation_data()
        images_path = os.path.realpath(images_path)
        self._write_png_timeseries(
            images_path,
            color=color,
            show_synapses=show_synapses,
            show_legend=show_legend,
            client=client,
            highlight_section=highlight_section,
            highlight_x=highlight_x,
            overwrite_frames=overwrite_frames)
        write_video_from_images(images_path,
                                out_path,
                                fps=1/tpf,
                                quality=quality,
                                codec=codec)

    def animation(
        self,
        images_path,
        overwrite_frames=False,
        color='grey',
        show_synapses=False,
        show_legend=False,
        client=None,
        t_start=None,
        t_stop=None,
        t_step=None,
        highlight_section=None,
        highlight_x=None,
        display=True,
        tpf=20):
        '''
        Creates a set of images where a neuron morphology color-coded with voltage together with synapse activations are
        shown for a set of time points. In each image the neuron rotates a bit (3 degrees) over its axis.
        These images are then put together into a python animation.
        The parameters :paramref:t_start, :paramref:t_stop and :paramref:t_step will define the :paramref:self.time attribute

        Args:
            - images_path: path where the images for the gif will be generated
            - t_start: start time point of our time series visualization
            - t_stop: last time point of our time series visualization
            - t_step: time between the different time points of our visualization
            - client: dask client for parallelization
            - neuron_rotation: rotation degrees of the neuron at each frame (in azimuth)
            - time_show_syn_activ: Time in the simulation during which a synapse activation is shown during the visualization
            - vmin: min voltages colorcoded in the cell morphology
            - vmax: max voltages colorcoded in the cell morphology (the lower vmax is, the stronger the APs are observed)
            - tpf: time per frame (in ms)
        '''
        assert self._has_simulation_data()
        self._update_times_to_show(t_start, t_stop, t_step)
        images_path = os.path.realpath(images_path)
        self._write_png_timeseries(
            images_path,
            color=color,
            show_synapses=show_synapses,
            show_legend=show_legend,
            client=client,
            highlight_section=highlight_section,
            highlight_x=highlight_x,
            overwrite_frames=overwrite_frames)
        if display:
            display_animation_from_images(images_path, tpf, embedded=True)

    def write_vtk_frames(
        self,
        out_name="frame",
        out_dir=".",
        t_start=None,
        t_stop=None,
        t_step=None,
        color=None,
        n_decimals=2,
        client=None):
        '''
        Format in which a cell morphology timeseries (color-coded with voltage) is saved to be visualized in paraview

        Args:
            out_name (str): name of the file (not path, the file will be generated in out_dir)
            out_dir (str): path where the images for the gif will be generated
            t_start (float): Update the start time of the visualization class-wide.
            t_stop (float): Update the stop time of the visualization class-wide.
            t_step (float): Update the time step of the visualization class-wide.
            color (str): If you want some other color overlayed on the cell morphology.
        '''
        scalar_data = {}

        if color is not None and self._has_simulation_data():
            self._update_times_to_show(t_start, t_stop, t_step)
        if isinstance(color, str) and color.lower() in ("voltage", "membrane voltage", "vm"):
            self._calc_voltage_timeseries()
            color_all_timepoints = [
                self._data_per_section_to_data_per_point(
                    self._get_voltages_at_timepoint(t)
                    ) for t in self.times_to_show]

        # add diameters by default
        scalar_data['diameter'] = self._morphology_unconnected['diameter'].values

        scattered_lookup_table = client.scatter(self._morphology_unconnected, broadcast=True) if client is not None else self._morphology_unconnected
        if client is None:
            logger.warning("No dask client provided. Images will be generated on a single thread, which may take some time.")
            client = Client(LocalCluster(n_workers=1, threads_per_worker=1))
        
        delayeds = []
        for i, t in enumerate(self.times_to_show):
            color_this_timepoint = color_all_timepoints[i]
            scalar_data[color] = color_this_timepoint
            out_name_ = out_name+ "_{:06d}.vtk".format(int(str(round(t, 2)).replace('.', '')))
            delayeds.append(
                dask.delayed(write_vtk_skeleton_file)(
                scattered_lookup_table,
                out_name_,
                out_dir,
                point_scalar_data=scalar_data,
                n_decimals=n_decimals))
        futures = client.compute(delayeds)
        client.gather(futures)
        logger.info("VTK files written to {}".format(out_dir))


class CellMorphologyInteractiveVisualizer(CMVDataParser):
    """Initialize a visualization class from a cell object, and extract relevant Cell data to a format that lends itself easier to plotting.
    It contains useful methods for interactively visualizing a cell morphology, the voltage along its body, or ion channel dynamics.
    It relies on Dash and Plotly to do so.
    """

    def __init__(
        self,
        cell,
        align_trunk=True,
        dash_ip=None,
        show=True,
        renderer="notebook_connected",
        t_start=None, t_stop=None, t_step=None):
        """
        Args:
            cell (:class:`~single_cell_parser.cell.Cell`): Cell object
            align_trunk (bool): Whether or not to align the cell trunk with the z-axis.
            dash_ip (str): IP address to run dash server on.
            show (bool): set to False for testing
            renderer (str): Type of backend renderer to use for rendering the javascript/HTML VBox. Defaults to "notebook_connected"
            t_start (float): start time point of our time series visualization
            t_stop (float): last time point of our time series visualization
            t_step (float): time between the different time points of our visualization
        """
        super().__init__(cell, align_trunk, t_start, t_stop, t_step)
        if dash_ip is None:
            dash_ip = socket.gethostbyname(socket.gethostname())
        self.dash_ip = dash_ip
        self.show = show  # set to False for testing
        self.renderer = renderer
        self.background_color="#f0f0f0"
        """IP address to run dash server on."""

    def _get_interactive_cell(
        self, 
        color=None,
        time_point=None,
        diameter=None):
        ''' 
        Setup plotly for rendering in notebooks.
        Shows an interactive 3D render of the Cell with NO data overlayed.

        Args:
            color (str | list): If you want some other color overlayed on the cell morphology. 
                Options: "voltage", "vm", "synapses", "synapse", or a color string, or a nested list of colors for each section
            time_point (float | int): time_point at which to plot some scalar data. Ignored when color does not refer to scalar data.
            diameter: If the actual diameter is poorly visible, set this value to a fixed diameter.

        Returns:
            plotly.graph_objs._figure.Figure: an interactive figure. Usually added to a ipywidgets.VBox object
        '''

        py.init_notebook_mode()
        pio.renderers.default = self.renderer
        transparent = "rgba(0, 0, 0, 0)"
        ax_layout = dict(
            backgroundcolor=transparent,
            gridcolor=transparent,
            showbackground=True,
            zerolinecolor=transparent,
            visible=False)

        # Create figure
        marker_markup = {
            'line': {'width': 0},
            'size': self._morphology_unconnected['diameter']
            }  # remove outline of markers
        color = self._data_per_section_to_data_per_point(
                self._calc_scalar_data_from_keyword(
                    color, time_point, return_as_color=False))
        if color is not None:
            marker_markup['color'] = color
        marker_markup['size'] = self._morphology_unconnected['diameter'] if diameter is None else [diameter]*len(self._morphology_unconnected)
        hover_text = ["section {}".format(e) for e in self._morphology_unconnected["sec_n"]]
        
        fig = go.FigureWidget(
            [
                go.Scatter3d(
                    x=self._morphology_unconnected["x"].values,
                    y=self._morphology_unconnected["y"].values,
                    z=self._morphology_unconnected["z"].values,
                    mode='markers',
                    opacity=1,
                    marker=marker_markup,
                    text=hover_text)
                ])
        
        fig.update_layout(
            scene=dict(
                xaxis=ax_layout,
                yaxis=ax_layout,
                zaxis=ax_layout,
                bgcolor=transparent  # turn off background for just the scene
            ),
            plot_bgcolor=self.background_color,
            paper_bgcolor=self.background_color,
            margin=dict(l=10, r=10, t=40, b=10))
        
        return fig

    def _get_interactive_dash_app(
        self,
        color,
        t_start, t_stop, t_step,
        ):
        """This is the main function to set up an interactive plot with scalar data overlayed.
        It fetches the scalar data of interest (usually membrane voltage, but others are possible; check with self.possible_scalars).
        It only fetches data for the time points specified in self.times_to_show, as only these timepoints will be plotted out.

        Args:
            color (str, optional): Scalar data to overlay on interactive plot. Defaults to None.
            background_color (str, optional): Background color of plot. Defaults to "rgb(180,180,180)".
            renderer (str, optional): Type of backend renderer to use for rendering the javascript/HTML VBox. Defaults to "notebook_connected".

        Returns:
            ipywidgets.VBox object: an interactive render of the cell.
        """
        self._update_times_to_show(t_start, t_stop, t_step)
        sections = self._morphology_unconnected['sec_n']

        #------------ Create figure
        # Interactive cell
        fig_cell = self._get_interactive_cell()
        fig_cell.add_trace(
            go.Scatter3d(
                x=[0], y=[0], z=[0],
                marker=dict(
                    size=10,
                    color="yellow")))

        dcc_cell = dcc.Graph(figure=fig_cell, id="dcc_cell")

        # Voltage traces
        scalar_pointdata_per_time = [
            self._data_per_section_to_data_per_point(
                self._calc_scalar_data_from_keyword(color, time_point, return_as_color=False))
            for time_point in self.times_to_show]
        color_per_time = {
            time_point: scalar_pointdata_per_time[t_idx]
            for t_idx, time_point in enumerate(self.times_to_show)}
        fig_trace = px.line(
            x=self.times_to_show,
            y=[s[0] for s in scalar_pointdata_per_time],
            labels={
                "x": "time (ms)",
                "y": color
            },
            title="{} at soma".format(color))
        dcc_trace = dcc.Graph(figure=fig_trace, id="dcc_trace")

        # display the FigureWidget and slider with center justification
        slider = dcc.Slider(
            min=self.t_start,
            max=self.t_stop,
            step=self.t_step,
            value=self.t_start,
            id="time-slider",
            updatemode='drag',
            marks=None,
            tooltip={
                "placement": "bottom",
                "always_visible": True
            })

        # Start dash app
        app = Dash(__name__)
        app.layout = html.Div(
            [dcc_cell, dcc_trace,
             html.Div(slider, id="output-container")])

        # update color scale
        @app.callback(
            Output('dcc_cell', 'figure'),
            Output('dcc_trace', 'figure'),
            inputs={
                "all_inputs": {
                    "time": Input("time-slider", "value"),
                    "click": Input("dcc_cell", "clickData"),
                    #"relayout": Input("dcc_cell", "relayoutData")
                }
            },)
        def _update(all_inputs):
            """
            Function that gets called whenever the slider gets changed. Requests the membrane voltages at a certain time point
            """
            def _update_trace(c):
                if c.click.triggered:
                    clicked_point_properties = c.click.value["points"][0]
                    point_ind = clicked_point_properties["pointNumber"]
                    # update the voltage trace widget
                    fig_trace.data[0]['y'] = [s[point_ind] for s in scalar_pointdata_per_time]
                    fig_trace.layout.title = "{} trace of point {}, section {}".format(
                        color, point_ind, int(sections[point_ind]))
                else:
                    time_point = c.time.value
                    fig_trace.update_layout(
                        shapes=[dict(
                            type='line',
                            yref='y domain',
                            y0=0,
                            y1=1,
                            xref='x',
                            x0=time_point,
                            x1=time_point)])
            def _update_cell(c):
                if c.click.triggered:
                    clicked_point_properties = c.click.value["points"][0]
                    point_ind = clicked_point_properties["pointNumber"]
                    for e in ['x', 'y', 'z']:
                        # update the yellow highlight point
                        fig_cell.data[1][e] = [clicked_point_properties[e]]
                else:
                    # triggered by either time slider or initial load
                    time_point = c.time.value
                    keys = np.array(sorted(list(color_per_time.keys())))
                    closest_time_point = keys[np.argmin(np.abs(keys - time_point))]
                    logger.info('requested_timepoint', time_point, 'selected_timepoint',
                        closest_time_point)
                    fig_cell.data[0].marker.color = color_per_time[closest_time_point]
                    fig_cell.layout.title = "{} at time={} ms".format(
                        color, time_point)
            c = ctx.args_grouping.all_inputs
            _update_cell(c)
            _update_trace(c)
            return fig_cell, fig_trace

        return app

    def interactive_plot(
        self,
        color="grey",
        renderer="notebook_connected",
        diameter=None,
        time_point=None,
        show=True):
        """This method shows a plot with an interactive cell, overlayed with scalar data (if provided with the data argument).
        The parameters :paramref:t_start, :paramref:t_stop and :paramref:t_step will define the :paramref:self.time attribute

        Args:
            color (str | list): 
                If you want some other color overlayed on the cell morphology. 
                Options: "voltage", "vm", "synapses", "synapse", or a color string, or a nested list of colors for each section
            time_point (float | int): time_point at which to plot some scalar data. Ignored when color does not refer to scalar data.
            diameter: If the actual diameter is poorly visible, set this value to a fixed diameter.
        
        """
        if self._keyword_is_scalar_data(color) and time_point is None:
            raise ValueError("You passed scalar data {} as a color, but didn't provide a timepoint at which to plot this. Please specify time_point.".format(color))
        pio.renderers.default = renderer
        f = self._get_interactive_cell(color, diameter=diameter, time_point=time_point)
        if show:
            f.show(renderer=renderer)
            return
        return f  # show is not True, return the object without executing the method that shows it

    def interactive_app(
        self,
        color="grey",
        renderer="notebook_connected",
        t_start=None, t_stop=None, t_step=None):
        """
        Args:
            color (str | list): 
                If you want some other color overlayed on the cell morphology. 
                Options: "voltage", "vm", "synapses", "synapse", or a color string, or a nested list of colors for each section
            renderer (str): 
                Available renderers:
                ['plotly_mimetype', 'jupyterlab', 'nteract', 'vscode', 'notebook', 'notebook_connected', 'kaggle', 'azure', 'colab',
                'cocalc', 'databricks', 'json', 'png', 'jpeg', 'jpg', 'svg', 'pdf', 'browser', 'firefox', 'chrome', 'chromium', 
                'iframe', 'iframe_connected', 'sphinx_gallery', 'sphinx_gallery_png']
            t_start (float): start time point of our time series visualization
            t_stop (float): last time point of our time series visualization
            t_step (float): time interval
        """
        # f is a dash app
        f = self._get_interactive_dash_app(color, t_start, t_stop, t_step,)
        return f.run_server(
            debug=True,
            use_reloader=False,
            port=5050,
            host=self.dash_ip)

def get_3d_plot_morphology(
    lookup_table=None,
    colors="grey",
    color_keyword=None,
    synapses={},
    time_point=None,
    highlight_section_kwargs={'sec_n': None, 'highlight_x': None, 'arrow_args': {}},
    camera_position={'azim': 0, 'dist': 10, 'elev': 30, 'roll': 0},
    dpi=72,
    population_to_color_dict={},
    save='',
    plot=False,
    synapse_legend=True,
    legend=None,
    return_figax = True,
    proj_type="ortho"
    ):
    """Constructs a 3d matplotlib plto of a cell morphology, overlayed with some scalar data.
    This method Uses LineCollections to plot the morphology, with a round joinstyle. 
    This method is usually not called directly. Rather, :class:`~CellMorphologyVisualizer` calls this method to generate a plot,
    depending on parameters such as parallellization client, scalar data overlay, viewing angles etc...
    It is recommended to use the high-level method :class:`~CellMorphologyVisualizer.plot` instead of trying to use this one directly.
    
    Note:
        See also: https://matplotlib.org/stable/gallery/lines_bars_and_markers/joinstyle.html
        
    Args:
        lookup_table (pd.DataFrame): 
            pandas DataFrame with the morphology of the cell, where the initial point of each section is duplicated: once for the same section, and once as the last point of the previous section.
        colors (str | array): Color for the voltage. Either a single color for all sections, or a list of colors for each section.
        color_keyword (str): Keyword for the scalar data to be saved. Defaults to only diameter.
        synapses (dict): Dictionary with synapse activations. Keys are the population names, values are lists of synapse locations.
        time_point (float): Time point at which to plot the scalar data.
        highlight_section_kwargs (dict): Additional arguments for the arrow. See available kwargs on https://matplotlib.org/3.1.1/api/_as_gen/matplotlib.patches.Arrow.html#matplotlib.patches.Arrow
        camera_position (dict): Camera angles and distance for matplotlib 3D visualizations. Possible keys: 'azim', 'dist', 'elev', 'roll'
        dpi (int): Image quality. Default: 72
        population_to_color_dict (dict): Dictionary to map synapse group names (str) to colors. Must contain the same keys as synapses.keys()
        save (str): Path where the plot will be saved. If it's empty it will not be saved (Default)
        plot (bool): whether to show the plot. Default: False
        synapse_legend (bool): Whether the synapse activations legend should appear in the plot
        legend (bool): Whether the legend for scalar data (e.g. membrane voltage) should appear in the plot
        return_figax (bool): Whether to return the figure and axis objects. Default: True
        proj_type (str): Projection type for the 3D plot. Default: "ortho"
    
    Returns:
        tuple|None: fig and ax object if :paramref:`return_figax` is True. None otherwise.
    """
    #----------------- Generic axes setup
    fig = plt.figure(
        figsize=(15, 15), 
        dpi=dpi,
        num=str(time_point))
    ax = plt.axes(projection='3d', proj_type=proj_type)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    plt.axis('off')
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_zlabel('z')
    ax.azim, ax.dist, ax.elev, ax.roll = camera_position['azim'], camera_position['dist'], camera_position['elev'], camera_position['roll']

    #----------------- map color
    sections = lookup_table['sec_n'].unique()
    if isinstance(colors, str):
        colors = [colors for _ in sections]
    else:
        assert len(colors) == len(sections), \
            "Number of colors ({}) does not match number of sections ({}). Either provide one color per section, or group line segment colors by section.".format(len(colors), len(sections))

    #----------------- plot neuron morphology
    for sec_n in sections:
        points = lookup_table[lookup_table['sec_n'] == sec_n]
        linewidths = points['diameter'][:-1].values + points['diameter'][1:].values / 2 #* 1.5 + 0.2 
        points = points[['x', 'y', 'z']].values.reshape(-1, 1, 3)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        lc = Line3DCollection(
            segments, 
            linewidths=linewidths, 
            color=colors[sec_n],
            joinstyle="bevel",
            capstyle="round")
        ax.add_collection(lc)

    ax.auto_scale_xyz(lookup_table['x'], lookup_table['y'], lookup_table['z'])
    
    #----------------- plot arrow, if necessary
    if highlight_section_kwargs['sec_n'] is not None or highlight_section_kwargs['highlight_x'] is not None:
        draw_arrow(lookup_table,
                    ax,
                    highlight_section=highlight_section_kwargs['sec_n'],
                    highlight_x=highlight_section_kwargs['highlight_x'],
                    highlight_arrow_kwargs=highlight_section_kwargs['arrow_args'])
    ax.set_box_aspect([
        ub - lb
        for lb, ub in (getattr(ax, 'get_{}lim'.format(a))() for a in 'xyz')
    ])
    
    #----------------- Plot synapse activations
    if synapses:
        for population in synapses.keys():
            for synapse in synapses[population]:
                color = population_to_color_dict[population]
                ax.scatter3D(
                    *synapse,
                    color=color,
                    edgecolors='grey',
                    s=75)
    if synapse_legend:
        synapse_legend_ax = fig.add_axes([0.70, 0.43, 0.05, 0.2])
        synapse_legend_ax.axis("off")
        handles = []
        for key in population_to_color_dict.keys():
            if key != 'inactive':
                handles.append(
                    mpatches.Patch(
                        color=population_to_color_dict[key], label=key))
        synapse_legend_ax.legend(
            handles=handles,
            fontsize=12)
    
    #----------------- Plot legend
    if legend is not None:
        cbaxes = fig.add_axes([0.64, 0.13, 0.05, 0.5])  # 0.64, 0.2, 0.05, 0.5
        cbaxes.axis("off")
        fig.colorbar(
            legend, 
            ax=cbaxes,      
            orientation='vertical',  
            label=color_keyword,
            fraction=0.2,
            ticks=np.linspace(legend.get_clim()[0], legend.get_clim()[1], 10))
        
    if time_point is not None:
        ax.text2D(
            x=0.7, y=0.7,
            s="Time = {:.2f} ms".format(time_point), 
            transform=ax.transAxes,
            fontsize=12)

    if save != '':
        fig.savefig(
            save, 
            edgecolor='none',
            dpi=dpi,
            bbox_inches='tight')
    if plot: 
        plt.show()
    if return_figax: 
        return fig, ax
    plt.close(fig)
