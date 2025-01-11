'''

'''

#from neuron import h, nrn
import numpy as np
from . import synapse
from collections import Sequence
import neuron

nrn = neuron.nrn
h = neuron.h
from itertools import chain
from . import analyze as sca
import pandas as pd
import json
import logging

__author__  = "Robert Egger"
__credits__ = ["Robert Egger", "Arco Bast"]
__date__    = "2012-04-28"

logger = logging.getLogger("ISF").getChild(__name__)


class Cell(object):
    '''Cell object providing API to the NEURON hoc interface.
    
    This class contains info on the cell morphology structure, and simulation data of single-cell simulations.
    The main purpose is to be a dataclass containing this information, but not to create or configure it on its own.
    Its attributes are set by :py:class:`~single_cell_parser.cell_parser.CellParser`.
    
    See also: 
        This is not the same class as :py:class:`singlecell_input_mapper.singlecell_input_mapper.cell.Cell`.
        This class concerns itself with providing API to NEURON, not with mapping input to the cell.
    
    Attributes: 
        hoc_path (str): Path to the hoc file containing the cell morphology.
        id (str | int, optional): ID of the cell (often unused).
        soma (:py:class:`~single_cell_parser.cell.PySection`): The soma section of the cell.
        tree (neuron.h.SectionList): NEURON SectionList containing all sections of the cell.
        branches (dict): maps the section ID (str) of the root section of each dendritic subtree to its corresponding section list (neuron.h.SectionList).
        structures (dict): All sections, aggregated by label (e.g. Dendrite, ApicalDendrite, ApicalTuft, Myelin...). Keys are labels (str), values are lists of :py:class:`~single_cell_parser.cell.PySection`s.
        sections (list): List of all :py:class:`~single_cell_parser.cell.PySection`s. sections[0] is the soma. Each section contains recorded data (if any was recorded, e.g. membrane voltage): a 2D array where axis 0 is segment number, and axis 1 is time.
        synapses (dict): a dictionary of lists of :py:class:`single_cell_parser.synapse.Synapse` objects
        E (float): Default resting membrane potential. Defaults to -70.0
        changeSynParamDict (dict): dictionary of network parameter sets with keys corresponding to time points. Allows automatic update of parameter sets according to their relative timing.
        tVec (neuron.h.Vector): a hoc Vector recording time.
        neuron_param: The :ref:`cell_parameters_format`.
        section_adjacency_map (dict): maps each section (by ID) to its parent sections and children sections.
        evokedNW: The :py:class:`single_cell_parser.network.NetworkMapper` object for evoked network simulations. 
            Set by e.g. :py:meth:`~single_cell_parser.cell_modify_functions.synaptic_input.synaptic_input`.
    '''
    def __init__(self):
        self.hoc_path = None
        self.id = None
        self.soma = None
        self.tree = None  # TODO: implement trees in python to avoid NEURON section stack problems that may occur during use of SectionLists
        self.branches = {}
        self.structures = {}
        self.sections = []
        self.synapses = {}
        self.E = -70.0  # TODO: this should be read in from the paramfile (e_pas)
        self.changeSynParamDict = {}
        self.tVec = None
        self.neuron_param = None
        self.neuron_sim_param = None  # TODO: is this used?
        self.network_param = None  # TODO: is this used?
        self.network_sim_param = None  # TODO: is this used?
        self.section_adjacency_map = None

    def re_init_cell(self, replayMode=False):
        '''Re-initialize for next simulation run.
        
        Cleans up the NEURON vectors and disconnects all synapses.
        
        Args:
            replayMode (bool): 
                If True, the cell is re-initialized for replay mode and all synapses are removed.
                Useful if a new network realization is to be used for the next simulation.
                Defaults to False.'''
        for sec in self.sections:
            sec._re_init_vm_recording()
            sec._re_init_range_var_recording()
        for synType in list(self.synapses.keys()):
            for syn in self.synapses[synType]:
                syn.disconnect_hoc_synapse()
            if replayMode:
                self.synapses[synType] = []

    def record_range_var(self, var, mech=None):
        """Record a range mechanism in all sections.
        
        Args:
            var (str): The name of the range mechanism to record.
            
        Example:
        
            >>> cell.record_range_var('Ca_HVA.ica')
        """
        
        #allow specifying mech and var in var. this is closer to the neuron syntax
        if '.' in var:
            mech, var = var.split('.')

        for sec in self.sections:
            try:
                sec._init_range_var_recording(var, mech)
            except (NameError, AttributeError):
                ## if mechanism not in segment: continue
                ## this leaves the duty to take care of missing range vars to
                ## all further functions relying on that values. I.e. they should
                ## check, if the range var is existent in the respective segment or not
                pass

    def distance_between_pts(self, sec1, x1, sec2, x2):
        """
        Computes the path length between two points.
    
        Points are specified by either their locations, or by point IDs and section IDs.
        
        Currently, this function uses the built-in NEURON method ``distance`` to compute the distances.
        Note that this approach may be inefficient for large numbers of synapses due to repeated computations.
        Additionally, the computed distances are approximate since NEURON calculates distances between the centers of segments.
    
        Future improvements could include implementing a look-up table for pair-wise distances to enhance efficiency.
    
        Args:
            x1 (float | int): Location or point ID of the first point.
            x2 (float | int): Location or point ID of the second point.
            sec1 (Section | int): Section or section ID containing the first point.
            sec2 (Section | int): Section or section ID containing the second point.
    
        Returns:
            float: The computed path length between the two points.
        """
        if isinstance(sec1, int):
            sec1 = self.sections[sec1]
            sec2 = self.sections[sec2]
            x1 = sec1.relPts(x1)
            x2 = sec2.relPts(x2)
        # set origin
        silent = h.distance(0, x1, sec=sec1)
        return h.distance(x2, sec=sec2)

    def distance_to_soma(self, sec, x):
        '''Computes the path length between the soma and a specified point.
        
        The point is specified by its location :paramref:`x` in the section :paramref:`sec`, or by the point ID :paramref:`x` and section ID :paramref:`sec`.
        
        Args:
            sec (Section | int): Section or section ID containing the point.
            x (float | int): Location or point ID of the point.
            
        Returns:
            float: The computed path length between the soma and the specified point.
        '''
        #        assume the user knows what they're doing...
        if isinstance(sec, int):
            return self.distance_between_pts(self.soma.secID, 0, sec, x)
        else:
            return self.distance_between_pts(self.soma, 0.0, sec, x)

    def max_distance(self, label):
        '''Computes maximum path length to soma of all branches with label :paramref:`label`
        
        Args:
            label (str): The label of the branches to consider.
            
        Returns:
            float: The maximum path length to the soma of all branches with label :paramref:`label`.
        '''
        if label == 'Soma':
            return self.soma.L
        maxDist = 0.0

        if label == "SpineHead" or label == "SpineNeck":
            distances = [
                self.distance_to_soma(sec, 1.0)
                for sec in self.sections
                if sec.label == label
            ]
            maxDist = max(distances)
        else:
            #        set origin to 0 of first branch with this label
            for sec in self.sections:
                if sec.label != label:
                    continue
                if sec.parent.label == 'Soma':
                    silent = h.distance(0, 0.0, sec=sec)
                    break
            for branchSectionList in self.branches[label]:
                for sec in branchSectionList:
                    secRef = h.SectionRef(sec=sec)
                    if not secRef.nchild():
                        #                    dist = self.distance_to_soma(sec, 1.0)
                        dist = h.distance(1.0, sec=sec)
                        if dist > maxDist:
                            maxDist = dist
        return maxDist

    def add_synapse(
        self,
        secID,
        ptID,
        ptx,
        preType='Generic',
        postType='Generic'):
        """Add a :py:class:`~single_cell_parser.synapse.Synapse` to the cell object.
        
        Args:
            secID (int): The section ID of the synapse location.
            ptID (int): The point ID of the synapse location.
            ptx (float): The relative coordinate along the section.
            preType (str, optional): The presynaptic cell type. Defaults to 'Generic'.
            postType (str, optional): The postsynaptic cell type. Defaults to 'Generic'.
        
        Returns:
            :py:class:`~single_cell_parser.synapse.Synapse`: The newly created synapse.
        """
        if preType not in self.synapses:
            self.synapses[preType] = []
        newSyn = synapse.Synapse(secID, ptID, ptx, preType, postType)
        newSyn.coordinates = np.array(self.sections[secID].pts[ptID])
        self.synapses[preType].append(newSyn)
        return self.synapses[preType][-1]

    def remove_synapses(self, preType=None):
        """Remove synapses from the cell object of type :paramref:`preType`.
        
        Args:
            preType (str, optional): 
                The type of synapses to remove. 
                If None, all synapses are removed.
                If 'All' or 'all', all synapses are removed.
                Otherwise, only synapses of the specified type are removed.
                Defaults to None.
        """
        if preType is None:
            return
        # remove all
        if preType == 'All' or preType == 'all':
            for synType in list(self.synapses.keys()):
                synapses = self.synapses[synType]
                del synapses[:]
                del self.synapses[synType]
            return


        # only one type
        else:
            try:
                synapses = self.synapses[preType]
                del synapses[:]
                del self.synapses[preType]
            except KeyError:
                logger.info('Synapses of type ' + preType + ' not present on cell')
            return

    def init_time_recording(self):
        """Initialize the NEURON time vector for recording.
        
        Initializes a time recording at the soma.
        """
        self.tVec = h.Vector()
        self.tVec.record(h._ref_t, sec=self.sections[0])

    def change_synapse_parameters(self):
        '''Change parameters of synapses during simulation.
        
        self.changeSynParamDict is dictionary of network parameter sets
        with keys corresponding to event times.
        This allows automatic update of parameter sets
        according to their relative timing.
        
        Raises:
            NotImplementedError: Synapse parameter change does not work correctly with VecStim.
        
        :skip-doc:
        '''
        raise NotImplementedError('Synapse parameter change does not work correctly with VecStim!')
        """ Old code
        eventList = self.changeSynParamDict.keys()
        eventList.sort()
        print 'Cell %s: event at t = %.2f' % (self.id ,eventList[0])
        tChange = eventList[0]
        newParamDict = self.changeSynParamDict.pop(eventList[0])
        synCnt = 0
        for synType in newParamDict.keys():
           print '\tchanging parameters for synapses of type %s' % synType
           for syn in self.synapses[synType]:
               synCnt += 1
               if not syn.is_active():
                   continue
               #===============================================================
               # re-compute release times in case release probability changes
               #===============================================================
               preChange = False
               for t in syn.preCell.spikeTimes:
                   if t >= tChange:
                       preChange = True
                       break
               if preChange:
                   changeBin = None
                   for i in range(len(syn.releaseSite.spikeTimes)):
                       if syn.releaseSite.spikeTimes[i] >= tChange:
                           changeBin = i
                   if changeBin is not None:
                       print '\tdetermine new release times for synapse %d of type %s' % (synCnt-1, synType)
                       print '\t\told VecStim: %s' % (syn.releaseSite.spikes)
                       del syn.releaseSite.spikeTimes[changeBin:]
                       syn.releaseSite.spikes.play()
                       syn.releaseSite.spikeVec.resize(0)
                       prelNew = newParamDict[synType].synapses.releaseProb
                       newSpikes = []
                       for t in syn.preCell.spikeTimes:
                           if t >= tChange:
                               if np.random.rand() < prelNew:
                                    # syn.releaseSite.append(t)
                                   newSpikes.append(t)
                                   syn.releaseSite.spikeTimes.append(t)
                                   print '\t\tnew release time %.2f' % (t)
                       if len(newSpikes):
                           print '\t\told NetCon: %s' % (syn.netcons[0])
                           print '\t\told NetCon valid: %d' % (syn.netcons[0].valid())
                           del syn.netcons[0]
                           # syn.netcons = []
                           print '\t\tcreating new VecStim'
                           del syn.releaseSite.spikes
                           syn.releaseSite.spikes = h.VecStim()
                           print '\t\tupdating SpikeVec:'
                           del syn.releaseSite.spikeVec
                           syn.releaseSite.spikeVec = h.Vector(newSpikes)
                           tRelStr = '\t\t'
                           for t in syn.releaseSite.spikeVec:
                               tRelStr += str(t)
                               tRelStr += ', '
                           print tRelStr
                           print '\t\tactivating new VecStim %s' % (syn.releaseSite.spikes)
                           syn.releaseSite.spikes.play(syn.releaseSite.spikeVec)
                           print '\t\tupdated VecStim %s with %d new spike times' % (syn.releaseSite.spikes, len(newSpikes))
                           
                           newSyn = synapse.Synapse(syn.secID, syn.ptID, syn.x, syn.preCellType, syn.postCellType)
                           newSyn.coordinates = np.array(self.sections[syn.secID].pts[syn.ptID])
                           newSyn.weight = syn.weight
                           newSyn.activate_hoc_syn(syn.releaseSite, syn.preCell, self, newParamDict[synType].synapses.receptors)
                           
                           syn.netcons = []
                           syn.receptors = {}
                           forget = syn
                           syn = newSyn
                           del forget
                           #===============================================================
                           # update biophysical parameters and NetCon
                           #===============================================================
#                            for recepStr in newParamDict[synType].synapses.receptors.keys():
#                                recep = newParamDict[synType].synapses.receptors[recepStr]
#                                hocStr = 'h.'
#                                hocStr += recepStr
#                                hocStr += '(x, sec=hocSec)'
#                                newSyn = eval(hocStr)
#                                del syn.receptors[recepStr]
#                                syn.receptors[recepStr] = newSyn
#                                for paramStr in recep.parameter.keys():
#                                #===========================================================
#                                # try treating parameters as NMODL range variables,
#                                # then as (global) NMODL parameters
#                                #===========================================================
#                                    try:
#                                        valStr = str(recep.parameter[paramStr])
#                                        cmd = 'syn.receptors[\'' + recepStr + '\'].' + paramStr + '=' + valStr
##                                        print 'setting %s for synapse of type %s' % (cmd, synType)
#                                        exec(cmd)
#                                    except LookupError:
#                                        cmd = paramStr + '_' + recepStr + '='
#                                        cmd += str(recep.parameter[paramStr])
##                                        print 'setting %s for synapse of type %s' % (cmd, synType)
#                                        h(cmd)
#                                threshParam = float(recep.threshold)
#                                delayParam = float(recep.delay)
#                                newNetcon = h.NetCon(syn.releaseSite.spikes, syn.receptors[recepStr])
##                                print '\t\told NetCon: %s' % (syn.netcons[0])
##                                print '\t\told NetCon valid: %d' % (syn.netcons[0].valid())
##                                del syn.netcons[0]
##                                syn.netcons = []
#                                syn.netcons = [newNetcon]
#                                print '\t\tnew NetCon: %s' % (syn.netcons[0])
#                                print '\t\tnew NetCon valid: %d' % (syn.netcons[0].valid())
#                                syn.netcons[0].threshold = threshParam
#                                syn.netcons[0].delay = delayParam
#                                if isinstance(recep.weight, Sequence):
#                                    for i in range(len(recep.weight)):
#                                        syn.netcons[0].weight[i] = recep.weight[i]
#                                else:
#                                    syn.netcons[0].weight[0] = recep.weight
    """

    def get_synapse_activation_dataframe(
        self,
        max_spikes=20,
        sim_trial_index=0):
        """Get a :ref:`syn_activation_format` dataframe.
        
        The :ref:`syn_activation_format` dataframe contains:
        
        - Synapse ID
        - Synapse type (i.e. presynaptic origin)
        - Synapse location: soma distance, section ID, section point ID, and dendrite label of the synapse
        - Activation times
        - The simulation trial index
        
        Args:
            max_spikes (int, optional): The maximum number of spikes (i.e. synaptic activations, not necessarily the same as spikes of the presynaptic cell) to write out. Defaults to 20.
            sim_trial_index (int, optional): The index of the simulation trial. Defaults to 0.
            
        Returns:
            pandas.DataFrame: The synapse activation dataframe.
        """
        syn_types = []
        syn_IDs = []
        spike_times = []
        sec_IDs = []
        pt_IDs = []
        dend_labels = []
        soma_distances = []

        for celltype in list(self.synapses.keys()):
            for syn in range(len(self.synapses[celltype])):
                if self.synapses[celltype][syn].is_active():
                    ## get list of active synapses' types and IDs
                    syn_types.append(celltype)
                    syn_IDs.append(syn)

                    ## get spike times
                    st_temp = [self.synapses[celltype][syn].releaseSite.spikeTimes[:]]
                    st_temp.append([np.nan] * (max_spikes - len(st_temp[0])))
                    st_temp = list(chain.from_iterable(st_temp))
                    spike_times.append(st_temp)

                    ## get info about synapse location
                    secID = self.synapses[celltype][syn].secID
                    sec_IDs.append(secID)
                    pt_IDs.append(self.synapses[celltype][syn].ptID)
                    dend_labels.append(self.sections[secID].label)

                    ## calculate synapse somadistances
                    sec = self.sections[secID]
                    soma_distances.append(
                        sca.compute_syn_distance(self,
                                                 self.synapses[celltype][syn]))

        ## write synapse activation df
        columns = [
            'synapse_type', 'synapse_ID', 'soma_distance', 'section_ID',
            'section_pt_ID', 'dendrite_label'
        ]
        sa_pd = dict(
            list(
                zip(columns, [
                    syn_types, syn_IDs, soma_distances, sec_IDs, pt_IDs,
                    dend_labels
                ])))
        sa_pd = pd.DataFrame(sa_pd)[columns]

        st_df = pd.DataFrame(columns=list(range(max_spikes)),
                             data=np.asarray(spike_times))

        sa_pd = pd.concat([sa_pd, st_df], axis=1)

        sa_pd.index = [sim_trial_index] * len(sa_pd)

        return sa_pd

    def get_section_adjacancy_map(self):
        """Generates a map that shows which sections are connected to which sections.
        
        Each section is mapped to its parent sections and children sections.
        
        Example:

            >>> cell.get_section_adjacancy_map()
            >>> cell.section_adjacency_map[0]["parents"]
            [None]  # soma has no parent sections
            >>> cell.section_adjacency_map[0]["children"]
            [1, 2, 3]

        Returns:
            dict: a dictionary where each key is the section id, and the value is a list of adjacent section ids
        """
        if self.section_adjacency_map is None:
            # Calculate the adjacency map
            # put parents in a dict
            section_adjacency_map = {}
            for child_section_n, section in enumerate(self.sections):
                # get parents
                section_adjacency_map[child_section_n] = {
                    "parents": [self.sections.index(section.parent)]
                               if section.parent else [],
                    "children": [
                        self.sections.index(c) for c in section.children()
                    ]
                }
            self.section_adjacency_map = section_adjacency_map
        return self.section_adjacency_map


class PySection(nrn.Section):
    '''Wrapper around :py:class:`nrn.Section` providing additional functionality for geometry and mechanisms.
    
    Attributes:
        label (str): label of the section (e.g. "Soma", "Dendrite", "Myelin").
        label_detailed (str, optional): 
            Detailed label of the section (e.g. "oblique", "basal", "trunk").
            These are manually assigned or automatically generated by :py:meth:`~biophysics_fitting.utils.augment_cell_with_detailed_labels`.
            Used in :py:meth:`~single_cell_parser.cell_modify_functions.scale_apical.scale_by_detailed_compartment`.
        parent (PySection): reference to parent section.
        parentx (float): connection point at parent section.
        bounds (tuple): bounding box around 3D coordinates.
        nrOfPts (int): number of traced 3D coordinates.
        pts (list): list of traced 3D coordinates.
        relPts (list): list of relative position of 3D points along section.
        diamList (list): list of diameters at traced 3D coordinates.
        area (float): total area of all NEURON segments in this section.
        segPts (list): list of segment centers (x coordinate). Useful for looping akin to the hoc function ``for(x)``. Excluding 0 and 1.
        segx (list): list of x values corresponding to center of each segment.
        segDiams (list): list of diameters of each segment. Used for visualization purposes only.
        recVList (list): list of neuron Vectors recording voltage in each compartment.
        recordVars (dict): dict of range variables recorded.
    '''

    def __init__(self, name=None, cell=None, label=None):
        '''
        Args:
            name (str, optional): name of the section
            cell (Cell, optional): reference to the cell object
            label (str, optional): label of the section
        '''
        if name is None:
            name = ''
        if cell is None:
            nrn.Section.__init__(self)
        else:
            nrn.Section.__init__(self, name=name, cell=cell)
        self.label = label
        self.parent = None
        self.parentx = 1.0
        self.bounds = ()
        self.nrOfPts = 0
        self.pts = []
        self.relPts = []
        self.diamList = []
        self.area = 0.0
        self.segPts = []
        self.segx = []
        self.segDiams = []
        self.recVList = []
        self.recordVars = {}

    def set_3d_geometry(self, pts, diams):
        '''Invokes NEURON 3D geometry setup.
        
        Args:
            pts (list): 3D coordinates of the section
            diams (list): diameters at the 3D coordinates.
            
        Raises:
            RuntimeError: If the list of diameters does not match the list of 3D points in length.
            
        Returns:
            None. Fills the attributes: ``pts``, ``nrOfPts``, ``diamList``, ``bounds``, and ``relPts``.
        '''
        if len(pts) != len(diams):
            errStr = 'List of diameters does not match list of 3D points'
            raise RuntimeError(errStr)
        self.pts = pts
        self.nrOfPts = len(pts)
        self.diamList = diams

        #        silent output in dummy instead of stdout
        dummy = h.pt3dclear(sec=self)
        for i in range(len(self.pts)):
            x, y, z = self.pts[i]
            d = self.diamList[i]
            dummy = h.pt3dadd(x, y, z, d, sec=self)

        # not good! set after passive properties have been assigned
        # self.nseg = self.nrOfPts

        self._compute_bounds()
        self._compute_relative_pts()
        # execute after nr of segments has been determined
        # self._init_vm_recording()

    def set_segments(self, nrOfSegments):
        '''Set spatial discretization.
        
        Spatial discretization bins the section points into segments. Each segment is a NEURON compartment with fixed diameter. 
        The amount of segments in each section is dependent on the biophysical properties of that section.
        This should thus be used together with biophysical parameters to produce meaningful, yet efficient discretization.
        
        Workflow:
        
        1. Determine the number of segments in the section.
        2. Compute the center points of each segment.
        3. Compute the diameter of each segment.
        4. Compute the total area of all NEURON segments in this section.
        5. Initialize voltage recording.
        
        See also
            :py:meth:`single_cell_parser.cell_parser.CellParser.determine_nseg`
        '''
        self.nseg = nrOfSegments
        self._compute_seg_pts()
        self._compute_seg_diameters()
        self._compute_total_area()
        #        TODO: find a way to make this more efficient,
        #        i.e. allocate memory before running simulation
        self._init_vm_recording()

    def _compute_seg_diameters(self):
        '''Computes the diameter of each segment in this section.
        
        Diameters are approximated for each segment by taking the diameter at the point closest to the segment center.
        '''
        self.segDiams = []
        for x in self.segx:
            minDist = 1.0
            minID = 0
            for i in range(len(self.relPts)):
                dist = abs(self.relPts[i] - x)
                if dist < minDist:
                    minDist = dist
                    minID = i
            self.segDiams.append(self.diamList[minID])

    def _compute_total_area(self):
        '''Computes total area of all NEURON segments in this section'''
        area = 0.0
        dx = 1.0 / self.nseg
        for i in range(self.nseg):
            x = (i + 0.5) * dx
            area += h.area(x, sec=self)
        self.area = area

    def _compute_bounds(self):
        """Computes the bounding box around the 3D coordinates."""
        pts = self.pts
        xMin, xMax = pts[0][0], pts[0][0]
        yMin, yMax = pts[0][1], pts[0][1]
        zMin, zMax = pts[0][2], pts[0][2]
        for i in range(1, len(pts)):
            if pts[i][0] < xMin:
                xMin = pts[i][0]
            if pts[i][0] > xMax:
                xMax = pts[i][0]
            if pts[i][1] < yMin:
                yMin = pts[i][1]
            if pts[i][1] > yMax:
                yMax = pts[i][1]
            if pts[i][2] < zMin:
                zMin = pts[i][2]
            if pts[i][2] > zMax:
                zMax = pts[i][2]
        self.bounds = xMin, xMax, yMin, yMax, zMin, zMax

    def _compute_relative_pts(self):
        """Computes the relative position of 3D points along the section.
        
        The relative position is the x-coordinate to the previous point.
        Ergo, the sum of :paramref:`relPts` should always equal 1.
        """
        self.relPts = [0.0]
        ptLength = 0.0
        pts = self.pts
        for i in range(len(pts) - 1):
            pt1, pt2 = np.array(pts[i]), np.array(pts[i + 1])
            ptLength += np.sqrt(np.sum(np.square(pt1 - pt2)))
            x = ptLength / self.L
            self.relPts.append(x)  # compared to previous point
        # avoid roundoff errors:
        norm = 1.0 / self.relPts[-1]
        for i in range(len(self.relPts) - 1):
            self.relPts[i] *= norm
        self.relPts[-1] = 1.0

    def _compute_seg_pts(self):
        '''Computes the 3D center points of each segment in this section.
        
        Approximates sections as a straight line.
        This data is only used for visualization purposes, not for simulating.        
        '''
        if len(self.pts) > 1:
            p0 = np.array(self.pts[0])
            p1 = np.array(self.pts[-1])
            vec = p1 - p0
            dist = np.sqrt(np.dot(vec, vec))
            vec /= dist
            #            endpoint stays the same:
            segLength = dist / self.nseg
            #            total length stays the same (straightening of dendrite;
            #             however this moves branch points):
            #            segLength = self.L/self.nseg
            for i in range(self.nseg):
                segPt = p0 + (i + 0.5) * segLength * vec
                self.segPts.append(segPt)
                self.segx.append((i + 0.5) / self.nseg)
        else:
            self.segPts = [self.pts[0]]

    def _init_vm_recording(self):
        '''Record the membrane voltage at every point in this section.
        
        Sets up a :py:class:`nrn.h.Vector` for recording membrane voltage at every segment in this section.
        '''
        # TODO: recVList[0] should store voltage recorded at
        # intermediate node between this and parent segment?
        #        beginVec = h.Vector()
        #        beginVec.record(self(0)._ref_v, sec=self)
        #        self.recVList.append(beginVec)
        for seg in self:
            vmVec = h.Vector()
            vmVec.record(seg._ref_v, sec=self)
            self.recVList.append(vmVec)


        # endVec = h.Vector()
        # endVec.record(self(1)._ref_v, sec=self)
        # self.recVList.append(endVec)

    def _re_init_vm_recording(self):
        '''Reinitialize votage recordings
        
        Resizes the :py:class:`nrn.h.Vector`s to 0 to avoid NEURON segfaults
        '''
        for vec in self.recVList:
            vec.resize(0)

    def _re_init_range_var_recording(self):
        '''Re-initialize the range mechanism recordings.
        
        Resizes the :py:class:`nrn.h.Vector`s to 0 to avoid NEURON segfaults
        '''
        for key in list(self.recordVars.keys()):
            for vec in self.recordVars[key]:
                vec.resize(0)

    def _init_range_var_recording(self, var, mech=None):
        """Initialize recording of a range mechanism.
        
        Args:
            var (str): The name of the range mechanism to record.
            mech (str, optional): The name of the mechanism. Defaults to None.
            
        Raises:
            NameError: If the mechanism is not present in the segment.
            AttributeError: If the mechanism is not present in the segment.
            
        Example:
        
            >>> sec._init_range_var_recording('ica', 'Ca_HVA')
        
        """
        if mech is None:
            if not var in list(self.recordVars.keys()):
                self.recordVars[var] = []
                for seg in self:
                    vec = h.Vector()
                    hRef = eval('seg._ref_' + var)
                    logger.info('seg._ref_' + var)
                    vec.record(hRef, sec=self)
                    self.recordVars[var].append(vec)
        else:
            if not var in list(self.recordVars.keys()):
                key = mech + '.' + var
                self.recordVars[key] = []
                for seg in self:
                    vec = h.Vector()
                    hRef = eval('seg.' + mech + '._ref_' + var)
                    #print ('seg.'+mech+'._ref_'+var)
                    vec.record(hRef, sec=self)
                    self.recordVars[key].append(vec)


class PointCell(object):
    '''Cell without morphological or electrophysiological features.

    Used as a presynaptic spike source for synapses. 
    Stores spike times in :py:class:`neuron.h.Vector` and :py:class:`numpy.array`.
    Requires :py:class:`nrn.h.VecStim` to trigger spikes at specified times.
        
    Attributes:
        spikeTimes (list): list of spike times. Default=None.
        spikeVec (:py:class:`neuron.h.Vector`): hoc Vector containing spike times
        spikes (:py:class:`neuron.h.VecStim`): 
            VecStim object to use as a spike source in :py:class:`~neuron.h.NetCon` objects (see https://www.neuron.yale.edu/neuron/static/py_doc/modelspec/programmatic/network/netcon.html).
            These are initialized from :paramref:`spikeTimes`.
        playing (bool): flag indicating whether the :py:class:`~neuron.h.VecStim` spike source is playing
        synapseList (list): list of synapses connected to this cell. 
    '''

    def __init__(self, spikeTimes=None):
        '''
        Args:
            spikeTimes (list): 
                List of precomputed spike times. 
                Used to initialize release sites with precomputed release times from presynaptic spike times (see :py:meth:`single_cell_parser.network.activate_functional_synapse`)
                Defaults to None.
        '''
        if spikeTimes is not None:
            self.spikeTimes = spikeTimes
            self.spikeVec = h.Vector(spikeTimes)
            self.spikes = h.VecStim()
        else:
            self.spikeTimes = []
            self.spikeVec = h.Vector()
            self.spikes = h.VecStim()
        self.playing = False
        self.synapseList = None
        self.spike_source = {}

    def is_active(self):
        """Check if the point cell is active."""
        return self.playing

    def play(self):
        '''Activate point cell'''
        if self.spikeVec.size() and not self.playing:
            self.spikes.play(self.spikeVec)
            self.playing = True

    def append(self, spikeT, spike_source=None):
        '''Append an additional spike time to the presynaptic cell.
        
        Used in :py:meth:`~single_cell_parser.network.NetworkMapper._create_pointcell_activities` to create a variety of spike times for presynaptic cells.
        
        Args:
            spikeT (float): Spike time.
            spike_source (str): Spike source category (see :py:meth:`single_cell_parser.network.NetworkMapper._create_pointcell_activities`)
        
        Raises:
            AssertionError: If the spike source is unknown.
        '''
        assert spike_source is not None
        self.spikeTimes.append(spikeT)
        self.spikeTimes.sort()
        self.spikeVec.append(spikeT)
        self.spikeVec.sort()
        self.playing = True
        self.spike_source[spikeT] = spike_source

    def compute_spike_train_times(
            self,
            interval,
            noise,
            start=0.0,
            stop=-1.0,
            nSpikes=None,
            spike_source=None):
        '''Compute a simple spike train for the presynaptic cell.
        
        For more sophisticated methods than a simple spike train, see :py:meth:`single_cell_parser.network.NetworkMapper._create_pointcell_activities`.
        
        Args:
            interval (float): Mean interval between spikes.
            noise (float): Noise parameter.
            start (float, optional): Start time of spike train. Defaults to 0.0.
            stop (float, optional): Stop time of spike train. Defaults to -1.0.
            nSpikes (int, optional): Number of spikes. Defaults to None.
            spike_source (str, optional): Spike source category (see :py:meth:`single_cell_parser.network.NetworkMapper._create_pointcell_activities`)
        '''
        assert spike_source is not None
        self.rand = np.random.RandomState(np.random.randint(123456, 1234567))
        self.spikeInterval = interval
        self.noiseParam = noise
        self.start = start
        self.stop = stop

        if self.stop < self.start and nSpikes is None:
            errstr = 'Trying to activate SpikeTrain without number of spikes or t stop parameter!'
            raise RuntimeError(errstr)

        if nSpikes is not None:
            lastSpike = 0.0
            for i in range(nSpikes):
                if i == 0:
                    tSpike = self.start + self._next_interval(
                    ) - self.spikeInterval * (1 - self.noiseParam)
                    if tSpike < 0:
                        tSpike = 0
                else:
                    tSpike = lastSpike + self._next_interval()
                self.append(tSpike, spike_source=spike_source)
                lastSpike = tSpike
        elif self.stop > self.start:
            lastSpike = 0.0
            while True:
                if lastSpike == 0:
                    tSpike = self.start + self._next_interval(
                    ) - self.spikeInterval * (1 - self.noiseParam)
                    if tSpike < 0:
                        tSpike = 0
                else:
                    tSpike = lastSpike + self._next_interval()
                if tSpike > self.stop:
                    break
                self.append(tSpike, spike_source=spike_source)
                lastSpike = tSpike


        # if self.spikeVec.size() and not self.playing:
        #     self.spikes.play(self.spikeVec)
        #     self.playing = True

    def _next_interval(self):
        """Calculate the next spike interval :math:`t` for a simple spike train.
        
        Includes both noise (:math:`\\sigma_{noise}`) and random variation (:math:`\\sigma_{rand}`) on the spike interval (:math:`\\Delta_t`):
        
        .. math::
        
            t = (1 - \\sigma_{noise}) \\cdot \\Delta_t + \\sigma_{noise} \\cdot \\Delta_t \\cdot \\sigma_{rand}
        
        Returns:
            float: The next spike interval.
        """
        if self.noiseParam == 0:
            return self.spikeInterval
        else:
            return (1 - self.noiseParam) * self.spikeInterval + self.noiseParam * self.spikeInterval * self.rand.exponential()

    def _add_synapse_pointer(self, synapse):
        """Add a reference to a synapse connected to this cell."""
        if self.synapseList is None:
            self.synapseList = [synapse]
        else:
            self.synapseList.append(synapse)

    def turn_off(self):
        '''Turns off the spike source.
        
        Calls ``play()`` with no arguments to turn off the :py:class:`~neuron.h.VecStim`.
        This is necessary because ``VecStim`` does not implement reference counting.
        Resizes the :py:class:`~neuron.h.Vector` to 0.
        
        Note:
            M. Hines: Note that one can turn off a VecStim without destroying it by using VecStim.play() with no args. 
            Turn it back on by supplying a Vector arg. Or one could resize the Vector to 0. :cite:t:`hines2001neuron`
        '''
        self.playing = False
        self.spikes.play()
        self.spikeTimes = []
        self.spikeVec.resize(0)


class SpikeTrain(PointCell):
    '''
    .. deprecated: 0.1.0 
        Only still in here in case some old dependency turns up that has not been found yet.
    
    Simple object for use as spike train source.
    Pre-computes spike times according to user-provided
    parameters and plays them as a regular point cell.
    Computation of spike times as in NEURON NetStim.
    
    :skip-doc:
    '''

    def __init__(self):
        PointCell.__init__(self)
        self.rand = np.random.RandomState(np.random.randint(123456, 1234567))
        self.spikeInterval = None
        self.noiseParam = 1.0
        self.start = 0.0
        self.stop = -1.0
        self.playing = False

    def set_interval(self, interval):
        self.spikeInterval = interval

    def set_noise(self, noise):
        self.noiseParam = noise

    def set_start(self, start):
        self.start = start

    def set_stop(self, stop):
        self.stop = stop

    def is_active(self):
        return self.playing

    def compute_spike_times(self, nSpikes=None):
        '''Activate point cell'''
        if self.spikeInterval is None:
            raise RuntimeError(
                'Trying to activate SpikeTrain without mean interval')
        if self.stop < self.start and nSpikes is None:
            errstr = 'Trying to activate SpikeTrain without number of spikes or t stop parameter!'
            raise RuntimeError(errstr)

        if nSpikes is not None:
            lastSpike = 0.0
            for i in range(nSpikes):
                if i == 0:
                    tSpike = self.start + self._next_interval(
                    ) - self.spikeInterval * (1 - self.noiseParam)
                    if tSpike < 0:
                        tSpike = 0
                else:
                    tSpike = lastSpike + self._next_interval()
                self.append(tSpike)
                lastSpike = tSpike
        elif self.stop > self.start:
            lastSpike = 0.0
            while True:
                if lastSpike == 0:
                    tSpike = self.start + self._next_interval(
                    ) - self.spikeInterval * (1 - self.noiseParam)
                    if tSpike < 0:
                        tSpike = 0
                else:
                    tSpike = lastSpike + self._next_interval()
                if tSpike > self.stop:
                    break
                self.append(tSpike)
                lastSpike = tSpike


#        if self.spikeVec.size() and not self.playing:
#            self.spikes.play(self.spikeVec)
#            self.playing = True

    def _next_interval(self):
        if self.noiseParam == 0:
            return self.spikeInterval
        else:
            return (
                1 - self.noiseParam
            ) * self.spikeInterval + self.noiseParam * self.spikeInterval * self.rand.exponential(
            )


class SynParameterChanger():
    """Change synapse parameters during simulation.
    
    Attributes:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        synParam (dict): The new :ref:`network_parameters_format` as a dictionary or :py:class:`~sumatra.NTParameterSet`.
        tEvent (float): Time at which the synapse parameters should change.
    """
    def __init__(self, cell, synParam, t):
        """
        Args:
            cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
            synParam (dict): The new :ref:`network_parameters_format` as a dictionary or :py:class:`~sumatra.NTParameterSet`.
            t (float): Time at which the synapse parameters should change.
        """
        self.cell = cell
        self.synParam = synParam
        self.tEvent = t
        self.cell.changeSynParamDict[self.tEvent] = self.synParam

    def cvode_event(self):
        """Add a CVode event to change the synapse parameters at time :paramref:`tEvent`."""
        h.cvode.event(self.tEvent, self.cell.change_synapse_parameters)
