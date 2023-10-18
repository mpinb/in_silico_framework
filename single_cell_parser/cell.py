'''
Created on Apr 28, 2012

@author: regger
'''

#from neuron import h, nrn
import numpy as np
from . import synapse
from collections import Sequence
import neuron
nrn = neuron.nrn
h = neuron.h
from itertools import chain
import single_cell_parser.analyze as sca
import pandas as pd
import json
import logging
log = logging.getLogger("ISF").getChild(__name__)

class Cell(object):
    '''
    Cell object providing morphological information
    and hoc interface
    '''
    
    def __init__(self):
        '''
        Constructor:
        
        self.id = None
        
        self.soma = None
        
        TODO: implement trees in python to avoid
        NEURON section stack problems that may occur
        during use of SectionLists
        tree and branches are set up by CellParser
        self.tree = None
        
        branches are all processes attached to soma
        self.branches = {}
        
        structures are all processes with different labels
        (e.g., Dendrite, ApicalDendrite, ApicalTuft, Myelin etc..
        self.structures = {}
        
        simply list of all sections
        self.sections = []
        
        self.synapses = {}
        
        TODO: this should be read from parameter file (e_pas)
        self.E = -70.0
        '''
        # TODO: right now, the cell information (points, connectivity, Vm...) has to be accessed on a section-by-section basis. Why isn't this information availabe as a flat array?
        # TODO: is it worth it to implement this extraction?

        self.hoc_path = None
        self.id = None
        self.soma = None
#        TODO: implement trees in python to avoid
#        NEURON section stack problems that may occur
#        during use of SectionLists
#        tree and branches are set up by CellParser
        self.tree = None
#        branches are all processes attached to soma
        self.branches = {}
#        structures are all processes with different labels
#        (e.g., Dendrite, ApicalDendrite, ApicalTuft, Myelin etc..
        self.structures = {}
#        simply list of all sections
        self.sections = []  # TODO: what type are these elements?
        self.synapses = {}
#        TODO: this should be read from parameter file (e_pas)
        self.E = -70.0
        self.changeSynParamDict = {}
        self.tVec = None
        self.neuron_param = None
        self.neuron_sim_param = None
        self.network_param = None
        self.network_sim_param = None
        self.section_adjacency_map = None
    
    def re_init_cell(self, replayMode=False):
        '''re-initialize for next simulation run'''
        for sec in self.sections:
            sec._re_init_vm_recording()
            sec._re_init_range_var_recording()
        for synType in list(self.synapses.keys()):
            for syn in self.synapses[synType]:
                syn.disconnect_hoc_synapse()
            if replayMode:
                self.synapses[synType] = []                
    
    def record_range_var(self, var, mech=None):
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
        '''computes path length between to points given by
        location x1 and x2 in sections sec1 and sec2
        or by ptID x1 and x2 and section ID sec1 and sec2.
        for now, use built-in NEURON method distance.
        This should probably be changed at some point in the future
        into something like a look-up table of pair-wise distances,
        because repeated computations for 1000s of synapses are going
        to be very expensive... also, only approximate, since NEURON
        computes distances between centers of segments'''
        if isinstance(sec1, int):
            sec1 = self.sections[sec1]
            sec2 = self.sections[sec2]
            x1 = sec1.relPts(x1)
            x2 = sec2.relPts(x2)
#        set origin
        silent = h.distance(0, x1, sec=sec1)
        return h.distance(x2, sec=sec2)
    
    def distance_to_soma(self, sec, x):
        '''computes path length between soma and point given by
        location x in sections sec or by ptID x and section ID sec'''
#        assume the user knows what they're doing...
        if isinstance(sec, int):
            return self.distance_between_pts(self.soma.secID, 0, sec, x)
        else:
            return self.distance_between_pts(self.soma, 0.0, sec, x)
    
    def max_distance(self, label):
        '''computes maximum path length to soma
        of all branches with the same label'''
        if label == 'Soma':
            return self.soma.L
        maxDist = 0.0

        if label == "SpineHead" or label == "SpineNeck":
            distances = [self.distance_to_soma(sec, 1.0) for sec in self.sections if sec.label == label]
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
    
    def add_synapse(self, secID, ptID, ptx, preType='Generic', postType='Generic'):
        if preType not in self.synapses:
            self.synapses[preType] = []
        newSyn = synapse.Synapse(secID, ptID, ptx, preType, postType)
        newSyn.coordinates = np.array(self.sections[secID].pts[ptID])
        self.synapses[preType].append(newSyn)
        return self.synapses[preType][-1]
    
    def remove_synapses(self, preType=None):
        if preType is None:
            return
#        remove all
        if preType == 'All' or preType == 'all':
            for synType in list(self.synapses.keys()):
                synapses = self.synapses[synType]
                del synapses[:]
                del self.synapses[synType]
            return
#        only one type
        else:
            try:
                synapses = self.synapses[preType]
                del synapses[:]
                del self.synapses[preType]
            except KeyError:
                log.info('Synapses of type ' + preType + ' not present on cell')
            return

    def init_time_recording(self):
        self.tVec = h.Vector()
        self.tVec.record(h._ref_t, sec = self.sections[0])          
    
    def change_synapse_parameters(self):
        '''
        Change parameters of synapses during simulation.
        self.changeSynParamDict is dictionary of network parameter sets
        with keys corresponding to event times.
        This allows automatic update of parameter sets
        according to their relative timing.
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
#                                    syn.releaseSite.append(t)
                                   newSpikes.append(t)
                                   syn.releaseSite.spikeTimes.append(t)
                                   print '\t\tnew release time %.2f' % (t)
                       if len(newSpikes):
                           print '\t\told NetCon: %s' % (syn.netcons[0])
                           print '\t\told NetCon valid: %d' % (syn.netcons[0].valid())
                           del syn.netcons[0]
#                            syn.netcons = []
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

    def get_synapse_activation_dataframe(self, max_spikes = 20, sim_trial_index = 0): 
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
                    st_temp.append([np.nan]* (max_spikes - len(st_temp[0])))
                    st_temp = list(chain.from_iterable(st_temp))
                    spike_times.append(st_temp)

                    ## get info about synapse location
                    secID = self.synapses[celltype][syn].secID
                    sec_IDs.append(secID)
                    pt_IDs.append(self.synapses[celltype][syn].ptID)
                    dend_labels.append(self.sections[secID].label)

                    ## calculate synapse somadistances
                    sec = self.sections[secID]
                    soma_distances.append(sca.compute_syn_distance(self, self.synapses[celltype][syn]))
                    

        ## write synapse activation df
        columns = ['synapse_type', 'synapse_ID', 'soma_distance', 'section_ID', 
                   'section_pt_ID', 'dendrite_label']
        sa_pd = dict(list(zip(columns, [syn_types, syn_IDs, soma_distances, sec_IDs, pt_IDs, dend_labels])))
        sa_pd = pd.DataFrame(sa_pd)[columns]
        
        st_df = pd.DataFrame(columns = list(range(max_spikes)), data = np.asarray(spike_times))
    
        sa_pd = pd.concat([sa_pd, st_df], axis = 1)
        
        

        sa_pd.index = [sim_trial_index] * len(sa_pd)


        return sa_pd

    def get_section_adjacancy_map(self):
        """Generates a map that shows which sections are connected to which sections.
        Saves this as a class attribute if it's the first time calculatingm otherwise returns

        Args:
            self (cell): the cell boject

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
                    "parents": [self.sections.index(section.parent)] if section.parent else [],
                    "children": [self.sections.index(c) for c in section.children()]
                    }
            self.section_adjacency_map = section_adjacency_map
        return self.section_adjacency_map

class PySection(nrn.Section):
    '''
    Subclass of nrn.Section providing additional geometric
    and mechanism information/ handling methods
    '''
    
    def __init__(self, name=None, cell=None, label=None):
        '''
        structure
        self.label = label
        
        reference to parent section
        self.parent = None
        
        connection point at parent section
        self.parentx = 1.0
        
        bounding box around 3D coordinates
        self.bounds = ()
        
        number of traced 3D coordinates
        self.nrOfPts = 0
        
        list of traced 3D coordinates
        self.pts = []
        
        list of relative position of 3D points along section
        self.relPts = []
        
        list of diameters at traced 3D coordinates
        self.diamList = []
        
        total area of all NEURON segments in this section
        self.area = 0.0
        
        list of center points of segments used during simulation
        self.segPts = []
        
        list of x values corresponding to center of each segment
        for looping akin to the hoc function for(x) (without 0  and 1)
        self.segx = []
        
        list of diameters of all segments
        self.segDiams = []
        
        list of neuron Vectors recording voltage in each compartment
        self.recVList = []
        
        dict of range variables recorded
        self.recordVars = {}
        '''
        if name is None:
            name = ''
        if cell is None:
            nrn.Section.__init__(self)
        else:
            nrn.Section.__init__(self, name=name, cell=cell)
        
        '''structure'''
        self.label = label
        '''reference to parent section'''
        self.parent = None
        '''connection point at parent section'''
        self.parentx = 1.0
        '''bounding box around 3D coordinates'''
        self.bounds = ()
        '''number of traced 3D coordinates'''
        self.nrOfPts = 0
        '''list of traced 3D coordinates'''
        self.pts = []
        '''list of relative position of 3D points along section'''
        self.relPts = []
        '''list of diameters at traced 3D coordinates'''
        self.diamList = []
        '''total area of all NEURON segments in this section'''
        self.area = 0.0
        '''list of center points of segments used during simulation (only for visualization)'''
        self.segPts = []
        '''list of x values corresponding to center of each segment
        for looping akin to the hoc function for(x) (without 0  and 1)'''
        self.segx = []
        '''list of diameters of all segments'''
        self.segDiams = []
        '''list of neuron Vectors recording voltage in each compartment'''
        self.recVList = []
        '''dict of range variables recorded'''
        self.recordVars = {}
    
    def set_3d_geometry(self, pts, diams):
        '''
        invokes NEURON 3D geometry setup
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
        
#        not good! set after passive properties have been assigned
#        self.nseg = self.nrOfPts
        
        self._compute_bounds()
        self._compute_relative_pts()
#        execute after nr of segments has been determined
#        self._init_vm_recording()
    
    def set_segments(self, nrOfSegments):
        '''
        Set spatial discretization. should be used
        together with biophysical parameters to produce
        meaningful, yet efficient discretization.
        calls private methods to initialize recordings etc.
        '''
        self.nseg = nrOfSegments
        self._compute_seg_pts()
        self._compute_seg_diameters()
        self._compute_total_area()
#        TODO: find a way to make this more efficient,
#        i.e. allocate memory before running simulation
        self._init_vm_recording()
    
    def _compute_seg_diameters(self):
        '''fill list of diameters of all segments.
        Approximation for visualization purposes only.
        Takes diameter at 3D point closest to segment center.'''
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
        '''computes total area of all NEURON segments in this section'''
        area = 0.0
        dx = 1.0/self.nseg
        for i in range(self.nseg):
            x = (i+0.5)*dx
            area += h.area(x, sec=self)
        self.area = area
    
    def _compute_bounds(self):
        pts = self.pts
        xMin, xMax = pts[0][0], pts[0][0]
        yMin, yMax = pts[0][1], pts[0][1]
        zMin, zMax = pts[0][2], pts[0][2]
        for i in range(1,len(pts)):
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
        self.relPts = [0.0]
        ptLength = 0.0
        pts = self.pts
        for i in range(len(pts)-1):
            pt1, pt2 = np.array(pts[i]), np.array(pts[i+1])
            ptLength += np.sqrt(np.sum(np.square(pt1-pt2)))
            x = ptLength/self.L
            self.relPts.append(x)
#        avoid roundoff errors:
        norm = 1.0/self.relPts[-1]
        for i in range(len(self.relPts)-1):
            self.relPts[i] *= norm
        self.relPts[-1] = 1.0
    
    def _compute_seg_pts(self):
        ''' compute 3D center points of segments
        by approximating section as straight line
        (only for visualization) '''
        if len(self.pts) > 1:
            p0 = np.array(self.pts[0])
            p1 = np.array(self.pts[-1])
            vec = p1 - p0
            dist = np.sqrt(np.dot(vec, vec))
            vec /= dist
#            endpoint stays the same:
            segLength = dist/self.nseg
#            total length stays the same (straightening of dendrite;
#             however this moves branch points):
#            segLength = self.L/self.nseg
            for i in range(self.nseg):
                segPt = p0 + (i+0.5)*segLength*vec
                self.segPts.append(segPt)
                self.segx.append((i+0.5)/self.nseg)
        else:
            self.segPts = [self.pts[0]]
    
    def _init_vm_recording(self):
        ''' set up recording of Vm at every point.
        TODO: recVList[0] should store voltage recorded at
        intermediate node between this and parent segment?'''
#        beginVec = h.Vector()
#        beginVec.record(self(0)._ref_v, sec=self)
#        self.recVList.append(beginVec)
        for seg in self:
            vmVec = h.Vector()
            vmVec.record(seg._ref_v, sec=self)
            self.recVList.append(vmVec)
#        endVec = h.Vector()
#        endVec.record(self(1)._ref_v, sec=self)
#        self.recVList.append(endVec)
    
    def _re_init_vm_recording(self):
        '''resize Vm vectors to 0 to avoid NEURON segfaults'''
        for vec in self.recVList:
            vec.resize(0)
    
    def _re_init_range_var_recording(self):
        '''resize Vm vectors to 0 to avoid NEURON segfaults'''
        for key in list(self.recordVars.keys()):
            for vec in self.recordVars[key]:
                vec.resize(0)
    
    def _init_range_var_recording(self, var, mech=None):
        if mech is None:
            if not var in list(self.recordVars.keys()):
                self.recordVars[var] = []
                for seg in self:
                    vec = h.Vector()
                    hRef = eval('seg._ref_'+var)
                    log.info('seg._ref_'+var)
                    vec.record(hRef, sec=self)
                    self.recordVars[var].append(vec)
        else:
            if not var in list(self.recordVars.keys()):
                key = mech+'.'+var
                self.recordVars[key] = []
                for seg in self:
                    vec = h.Vector()
                    hRef = eval('seg.'+mech+'._ref_'+var)
                    #print ('seg.'+mech+'._ref_'+var)
                    vec.record(hRef, sec=self)
                    self.recordVars[key].append(vec)


class PointCell(object):
    '''
    simple object for use as spike source
    stores spike times in hoc Vector and numpy array
    requires VecStim to trigger spikes at specified times
    
    initialize with list (iterable) of spike times
    '''
    
    def __init__(self, spikeTimes=None):
        '''
        self.spikeTimes = list(spikeTimes)
        self.spikeVec = h.Vector(spikeTimes)
        self.spikes = h.VecStim()
        
        for use as cell connecting to synapses, not directly to NetCons:
        self.synapseList = None
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
        return self.playing
    
    def play(self):
        '''Activate point cell'''
        if self.spikeVec.size() and not self.playing:
            self.spikes.play(self.spikeVec)
            self.playing = True
    
    def append(self, spikeT, spike_source = None):
        '''append additional spike time'''
        assert(spike_source is not None)
        self.spikeTimes.append(spikeT)
        self.spikeTimes.sort()
        self.spikeVec.append(spikeT)
        self.spikeVec.sort()
        self.playing = True
        self.spike_source[spikeT] = spike_source
    
    def compute_spike_train_times(self, interval, noise, start=0.0, stop=-1.0, nSpikes=None, spike_source = None):
        '''Activate point cell'''
        assert(spike_source is not None)
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
                    tSpike = self.start + self._next_interval() - self.spikeInterval*(1 - self.noiseParam)
                    if tSpike < 0:
                        tSpike = 0
                else:
                    tSpike = lastSpike + self._next_interval()
                self.append(tSpike, spike_source = spike_source)
                lastSpike = tSpike
        elif self.stop > self.start:
            lastSpike = 0.0
            while True:
                if lastSpike == 0:
                    tSpike = self.start + self._next_interval() - self.spikeInterval*(1 - self.noiseParam)
                    if tSpike < 0:
                        tSpike = 0
                else:
                    tSpike = lastSpike + self._next_interval()
                if tSpike > self.stop:
                    break
                self.append(tSpike, spike_source = spike_source)
                lastSpike = tSpike
        
#        if self.spikeVec.size() and not self.playing:
#            self.spikes.play(self.spikeVec)
#            self.playing = True
        
    def _next_interval(self):
        if self.noiseParam == 0:
            return self.spikeInterval
        else:
            return (1 - self.noiseParam)*self.spikeInterval + self.noiseParam*self.spikeInterval*self.rand.exponential()
    
    def _add_synapse_pointer(self, synapse):
        if self.synapseList is None:
            self.synapseList = [synapse]
        else:
            self.synapseList.append(synapse)
    
    def turn_off(self):
        '''M. Hines: Note that one can turn off a VecStim without destroying it
        by using VecStim.play() with no args. Turn it back on by
        supplying a Vector arg. Or one could resize the Vector to 0.
        necessary b/c vecevent.mod does not implement ref counting'''
        self.playing = False
        self.spikes.play()
        self.spikeTimes = []
        self.spikeVec.resize(0)


class SpikeTrain(PointCell):
    '''
    DEPRECATED: only still in here in case some old
    dependency turns up that has not been found yet.
    Simple object for use as spike train source.
    Pre-computes spike times according to user-provided
    parameters and plays them as a regular point cell.
    Computation of spike times as in NEURON NetStim.
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
            raise RuntimeError('Trying to activate SpikeTrain without mean interval')
        if self.stop < self.start and nSpikes is None:
            errstr = 'Trying to activate SpikeTrain without number of spikes or t stop parameter!'
            raise RuntimeError(errstr)
        
        if nSpikes is not None:
            lastSpike = 0.0
            for i in range(nSpikes):
                if i == 0:
                    tSpike = self.start + self._next_interval() - self.spikeInterval*(1 - self.noiseParam)
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
                    tSpike = self.start + self._next_interval() - self.spikeInterval*(1 - self.noiseParam)
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
            return (1 - self.noiseParam)*self.spikeInterval + self.noiseParam*self.spikeInterval*self.rand.exponential()

class SynParameterChanger():
    def __init__(self, cell, synParam, t):
        self.cell = cell
        self.synParam = synParam
        self.tEvent = t
        self.cell.changeSynParamDict[self.tEvent] = self.synParam
    
    def cvode_event(self):
        h.cvode.event(self.tEvent, self.cell.change_synapse_parameters)

