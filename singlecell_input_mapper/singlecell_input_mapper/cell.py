'''
Created on Apr 28, 2012

@author: regger
'''
from __future__ import absolute_import
import numpy as np
from . import reader


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
        
        structures are all processes with different labels
        (e.g., Dendrite, ApicalDendrite, ApicalTuft, Myelin etc..
        self.structures = {}
        
        simply list of all sections
        self.sections = []
        
        bounding box around all processes
        self.boundingBox = None
        
        self.synapses = {}
        '''
        self.id = None
        self.soma = None
        #        structures are all processes with different labels
        #        (e.g., Dendrite, ApicalDendrite, ApicalTuft, Myelin etc..
        self.structures = {}
        #        simply list of all sections
        self.sections = []
        #        bounding box around all processes
        self.boundingBox = None
        self.synapses = {}

    def distance_to_soma(self, sec, x):
        '''path length to soma from location x on section sec'''
        currentSec = sec
        parentSec = currentSec.parent
        #        parentSec = self.sections[currentSec.parentID]
        dist = x * currentSec.L
        parentLabel = parentSec.label
        while parentLabel != 'Soma':
            dist += parentSec.L
            currentSec = parentSec
            parentSec = currentSec.parent
            #            parentSec = self.sections[currentSec.parentID]
            parentLabel = parentSec.label
        return dist

    def get_bounding_box(self):
        if not self.boundingBox:
            xMin, xMax, yMin, yMax, zMin, zMax = self.sections[0].bounds
            for i in range(1, len(self.sections)):
                bounds = self.sections[i].bounds
                if bounds[0] < xMin:
                    xMin = bounds[0]
                if bounds[1] > xMax:
                    xMax = bounds[1]
                if bounds[2] < yMin:
                    yMin = bounds[2]
                if bounds[3] > yMax:
                    yMax = bounds[3]
                if bounds[4] < zMin:
                    zMin = bounds[4]
                if bounds[5] > zMax:
                    zMax = bounds[5]
            self.boundingBox = xMin, xMax, yMin, yMax, zMin, zMax
        return self.boundingBox

    def add_synapse(self,
                    secID,
                    ptID,
                    ptx,
                    preType='Generic',
                    postType='Generic'):
        if preType not in self.synapses:
            self.synapses[preType] = []
        newSyn = Synapse(secID, ptID, ptx, preType, postType)
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
                print('Synapses of type ' + preType + ' not present on cell')
            return


class PySection2(object):
    '''
    Modeled after nrn.Section to allow easy interface with
    existing methods for cell parsing/synapse mapping
    without any NEURON dependencies
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
        
        length of section
        self.L = 0.0
        '''
        if name is None:
            self.name = ''
        else:
            self.name = name
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
        '''length of section'''
        self.L = 0.0

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

        self._compute_bounds()
        self._compute_length()
        self._compute_relative_pts()

    def _compute_bounds(self):
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
        self.relPts = [0.0]
        ptLength = 0.0
        pts = self.pts
        for i in range(len(pts) - 1):
            pt1, pt2 = np.array(pts[i]), np.array(pts[i + 1])
            ptLength += np.sqrt(np.sum(np.square(pt1 - pt2)))
            x = ptLength / self.L
            self.relPts.append(x)


#        avoid roundoff errors:
        if len(self.relPts) > 1:
            norm = 1.0 / self.relPts[-1]
            for i in range(len(self.relPts) - 1):
                self.relPts[i] *= norm
            self.relPts[-1] = 1.0

    def _compute_length(self):
        length = 0.0
        pts = self.pts
        for i in range(len(pts) - 1):
            pt1, pt2 = np.array(pts[i]), np.array(pts[i + 1])
            length += np.sqrt(np.sum(np.square(pt1 - pt2)))
        self.L = length


class PointCell(object):
    '''
    simple object for use as cell connecting to synapses
    '''

    def __init__(self, column=None, cellType=None):
        '''
        for use as cell connecting to synapses:
        self.synapseList = None
        '''
        self.synapseList = None
        self.column = column
        self.cellType = cellType

    def _add_synapse_pointer(self, synapse):
        if self.synapseList is None:
            self.synapseList = [synapse]
        else:
            self.synapseList.append(synapse)


class Synapse(object):
    '''
    Synapse base class
    Contains information about pre- and postsynaptic cell type,
    branch ID of postsynaptic cell, branch pt ID,
    and xyz-coordinates of synapse location
    '''

    def __init__(self,
                 edgeID,
                 edgePtID,
                 edgex,
                 preCellType='',
                 postCellType=''):
        '''
        ID of attached section in cell.sections
        self.secID = edgeID
        
        ID of attached point in cell.sections[self.secID].pts
        self.ptID = edgePtID
        
        relatice coordinate along attached section
        self.x = edgex
        
        self.preCellType = preCellType
        reference to presynaptic cell (PointCell)
        self.preCell = None
        
        self.postCellType = postCellType
        
        3D coordinates of synapse location
        self.coordinates = None
        '''
        self.secID = edgeID
        self.ptID = edgePtID
        self.x = edgex
        self.preCellType = preCellType
        self.preCell = None
        self.postCellType = postCellType
        self.coordinates = None


class CellParser(object):
    '''
    class providing methods for setting up morphology in NEURON hoc object
    '''
    cell = None

    def __init__(self, hocFilename=''):
        '''
        Constructor
        '''
        self.hoc_fname = hocFilename

    def spatialgraph_to_cell(self):
        '''
        reads cell morphology from Amira hoc file
        and sets up PySections and Cell object
        optional: takes function object scaleFunc as argument
        for scaling dendritic diameters.
        scaleFunc takes cell object as argument
        '''
        edgeList = reader.read_hoc_file(self.hoc_fname)
        self.hoc_fname = self.hoc_fname.split('/')[-1]
        #part1 = self.hoc_fname.split('_')[0]
        #part2 = self.hoc_fname.split('_')[1]
        #part3 = self.hoc_fname.split('.')[-2]
        self.cell = Cell()
        self.cell.id = self.hoc_fname  # '_'.join([part1, part2, part3])

        #        first loop: create all Sections
        for edge in edgeList:
            sec = PySection2(edge.hocLabel, self.cell.id, edge.label)
            if sec.label != 'Soma':
                sec.parentx = edge.parentConnect
                sec.parentID = edge.parentID
            sec.set_3d_geometry(edge.edgePts, edge.diameterList)
            self.cell.sections.append(sec)
            if sec.label == 'Soma':
                self.cell.soma = sec


#        second loop: create structures dict and connectivity
#        between sections
        for sec in self.cell.sections:
            if sec.label != 'Soma':
                sec.parent = self.cell.sections[sec.parentID]
            if sec.label not in self.cell.structures:
                self.cell.structures[sec.label] = [sec]
            else:
                self.cell.structures[sec.label].append(sec)

    def get_cell(self):
        '''
        returns cell if it is set up
        '''
        if self.cell is None:
            raise RuntimeError(
                'Trying to access cell before morphology has been loaded')
        return self.cell
