'''Classes for setting up a cell morphology and mapping synapses onto it.

Used to create network realizations. 
For functional network realizations (i.e. known presynaptic origin of each synapse), see :py:mod:`single_cell_parser.network`
'''
from __future__ import absolute_import
import numpy as np
from . import reader
__author__ = 'Robert Egger'
__date__ = '2012-04-28'


class Cell(object):
    '''Cell object for mapping synapses onto a morphology.

    This is a leightweight dataclass specialized for use with :py:mod:`singlecell_input_mapper.singlecell_input_mapper.synapse_mapper`.

    See also: 
        This is not the same class as :py:class:`single_cell_parser.cell.Cell`.
        Contrary to :py:class:`single_cell_parser.cell.Cell`, this class does not provide any biophysical details,
        simulation parameters or biophysical details.

    Attributes:
        id (str): Unique identifier for the cell.
        soma (:py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.PySection2`): The soma section.
        structures (dict): Dictionary mapping section labels (e.g. "Soma", "Dendrite" ...) to a list of corresponding sections.
        sections (list): List of all sections.
        boundingBox (tuple): Bounding box around the cell.
        synapses (dict): Dictionary mapping presynaptic cell types to a list of :py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Synapse` objects.

    '''

    def __init__(self):
        self.id = None
        self.soma = None
        self.structures = {}
        self.sections = []
        self.boundingBox = None
        self.synapses = {}

    def distance_to_soma(self, sec, x):
        '''Calculate the path length to soma from location :paramref:`x` on section :paramref:`sec`

        Args:
            sec (:py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.PySection2`): Section object.
            x (float): Relative position along the section (0-1).

        Returns:
            float: Path length to soma in micrometer.
        '''
        currentSec = sec
        parentSec = currentSec.parent
        # parentSec = self.sections[currentSec.parentID]
        dist = x * currentSec.L
        parentLabel = parentSec.label
        while parentLabel != 'Soma':
            dist += parentSec.L
            currentSec = parentSec
            parentSec = currentSec.parent
            # parentSec = self.sections[currentSec.parentID]
            parentLabel = parentSec.label
        return dist

    def get_bounding_box(self):
        """Calculate the bounding box around the cell.
        
        Returns:
            tuple: 6-tuple bounding box around the cell: (xMin, xMax, yMin, yMax, zMin, zMax)."""
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

    def add_synapse(
        self,
        secID,
        ptID,
        ptx,
        preType='Generic',
        postType='Generic'):
        """Add a :py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Synapse` to the cell.
        
        Args:
            secID (int): Section ID.
            ptID (int): Point ID on that section.
            ptx (float): Relative position along the section (0-1).
            preType (str): Presynaptic cell type. Default: "Generic".
            postType (str): Postsynaptic cell type. Default: "Generic".
            
        Returns:
            :py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Synapse`: The newly created synapse.   
        """
        if preType not in self.synapses:
            self.synapses[preType] = []
        newSyn = Synapse(secID, ptID, ptx, preType, postType)
        newSyn.coordinates = np.array(self.sections[secID].pts[ptID])
        self.synapses[preType].append(newSyn)
        return self.synapses[preType][-1]

    def remove_synapses(self, preType=None):
        """Remove all synapses of type :paramref:`preType` from the cell.
        
        Args:
            preType (str): Presynaptic cell type. Default: None. Set to 'All' or 'all' to remove all synapses.

        Returns:
            None
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
                print('Synapses of type ' + preType + ' not present on cell')
            return


class PySection2(object):
    '''Convenience class around NEURON's Section class.

    Provides an interface with existing methods in ISF for cell 
    parsing and mapping synapses without any additional NEURON :cite:`hines2001neuron`
    dependencies.

    Attributes:
        name (str): 
            Name of the section.
        label (str): 
            Label of the section (e.g. "Soma", "Dendrite", "ApicalDendrite" ...).
        parent (:py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.PySection2`): 
            Parent section.
        parentx (float): 
            Relative position along the parent section (0-1).
            Usually, sections are split up on branch points, making parentx equal to 1.0, but
            this is not always the case (e.g. when the section has a similar diameter beyond the branch point).
        bounds (tuple): 
            Bounding box around the section.
        nrOfPts (int): 
            Number of traced 3D coordinates.
        pts (list): 
            List of traced 3D coordinates.
        relPts (list): 
            List of relative position of 3D points along the section.
        diamList (list): 
            List of diameters at traced 3D coordinates.
        L (float): 
            Length of the section.
    '''

    def __init__(self, name=None, cell=None, label=None):
        '''
        Args:
            name (str): Name of the section. Default: None.
            cell (str): Name of the cell. Default: None.
            label (str): Label of the section. Default: None.
        '''
        if name is None:
            self.name = ''
        else:
            self.name = name
        self.label = label
        self.parent = None
        self.parentx = 1.0
        self.bounds = ()
        self.nrOfPts = 0
        self.pts = []
        self.relPts = []
        self.diamList = []
        self.L = 0.0

    def set_3d_geometry(self, pts, diams):
        '''Invokes NEURON :cite:`hines2001neuron` 3D geometry setup

        Fetch the 3D coordinates and diameters of the section.
        Computes the bounding box, length, and relative position of the 3D points along the section.

        Args:
            pts (list): List of 3D coordinates.
            diams (list): List of diameters.
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
        """Compute the bounding box of the section.
        
        Returns:
            None. Set the bounding box in the format (xMin, xMax, yMin, yMax, zMin, zMax)."""
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
        """Compute the relative position of 3D points along the section.
        
        This methods transforms 3D coordinates to relative positions along the section.
        The relative position is denoted as `x` in the context of a section, and
        can take values between 0 (beginning of the section) and 1 (end of the section)."""
        self.relPts = [0.0]
        ptLength = 0.0
        pts = self.pts
        for i in range(len(pts) - 1):
            pt1, pt2 = np.array(pts[i]), np.array(pts[i + 1])
            ptLength += np.sqrt(np.sum(np.square(pt1 - pt2)))
            x = ptLength / self.L
            self.relPts.append(x)

        # avoid roundoff errors:
        if len(self.relPts) > 1:
            norm = 1.0 / self.relPts[-1]
            for i in range(len(self.relPts) - 1):
                self.relPts[i] *= norm
            self.relPts[-1] = 1.0

    def _compute_length(self):
        """Calculate the length of the section."""
        length = 0.0
        pts = self.pts
        for i in range(len(pts) - 1):
            pt1, pt2 = np.array(pts[i]), np.array(pts[i + 1])
            length += np.sqrt(np.sum(np.square(pt1 - pt2)))
        self.L = length


class PointCell(object):
    '''Cell object without morphological attributes.

    When connecting synapses between postsynaptic and
    presynaptic cells, this class is used for the presynaptic cell.

    Attributes:
        synapseList (list): List of synapses.
        column (str): Column ID.
        cellType (str): Cell type.
    '''

    def __init__(self, column=None, cellType=None):
        '''
        Args:
            column (str): Column ID. Default: None.
            cellType (str): Cell type. Defalut: None.
        '''
        self.synapseList = None
        self.column = column
        self.cellType = cellType

    def _add_synapse_pointer(self, synapse):
        """Add a synapse to the cell.
        
        NEURON's :cite:`hines2001neuron` Python hoc interface
        provides pointers to synapses, rather than the full object.
        
        Args:
            synapse (nrn.synapse): Synapse object."""
        if self.synapseList is None:
            self.synapseList = [synapse]
        else:
            self.synapseList.append(synapse)


class Synapse(object):
    '''Leightweight dataclass to store basic synapse information.
    
    Synapses are direct attributes of :py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.PySection2` objects, 
    which in turn are direct attributes of :py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell` objects.
    Contains information on: pre- and postsynaptic cell type, branch ID of postsynaptic cell, branch pt ID, 
    and xyz-coordinates of synapse location
    
    See also:
        This is not the same class as :py:class:`single_cell_parser.synapse.Synapse`.
        This is a leightweight dataclass specialized for use with :py:mod:`single_cell_input_mapper.synapse_mapper`,
        and does not contain any methods for NEURON API or synapse activations during simulations.
    
    Attributes:
        secID (int): Section ID.
        ptID (int): Point ID on that section.
        x (float): Relative position along the section (0-1).
        preCellType (str): Presynaptic cell type.
        preCell (:py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.PointCell`): Presynaptic cell.
        postCellType (str): Postsynaptic cell type.
        coordinates (numpy.ndarray): 3D coordinates of the synapse location.
    '''
    def __init__(
            self,
            edgeID,
            edgePtID,
            edgex,
            preCellType='',
            postCellType=''):
        '''
        Args:
            edgeID (ind): Section ID.
            edgePtID (int): Point ID on that section. 
            edgex (float): Relative position along the section (0-1).
            preCellType (str): Presynaptic cell type. Default: ''.
            postCellType (str): Postsynaptic cell type. Default: ''.
        '''
        self.secID = edgeID
        self.ptID = edgePtID
        self.x = edgex
        self.preCellType = preCellType
        self.preCell = None
        self.postCellType = postCellType
        self.coordinates = None


class CellParser(object):
    '''Extract cell morphology from an AMIRA hoc file.

    See also:
        This is not the same class as :py:class:`single_cell_parser.cell_parser.CellParser`.
        This is a leightweight dataclass specialized for use with :py:mod:`single_cell_parser.synapse_mapper.SynapseMapper`,
        and does not contain any biophysical details.

    Attributes:
        hoc_fname (str): File name of the hoc file.
        cell (:py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell`): Cell object.
    '''
    cell = None

    def __init__(self, hocFilename=''):
        '''
        Args:
            hocFilename (str): File name of the hoc file. Default: ''.
        '''
        self.hoc_fname = hocFilename

    def spatialgraph_to_cell(self):
        '''Set up a cell object from an AMIRA hoc file.
        
        Reads cell morphology from Amira hoc file
        and sets up PySections and Cell object.
            
        .. deprecated:: 1.0
            The `scaleFunc` argument is deprecated and will be removed in a future version.
            To ensure reproducability, scaleFunc should be specified in the cell parameters, as 
            described in :py:mod:`~single_cell_parser.cell_modify_funs`
        '''
        edgeList = reader.read_hoc_file(self.hoc_fname)
        self.hoc_fname = self.hoc_fname.split('/')[-1]
        #part1 = self.hoc_fname.split('_')[0]
        #part2 = self.hoc_fname.split('_')[1]
        #part3 = self.hoc_fname.split('.')[-2]
        self.cell = Cell()
        self.cell.id = self.hoc_fname  # '_'.join([part1, part2, part3])

        #        # first loop: create all Sections
        for edge in edgeList:
            sec = PySection2(edge.hocLabel, self.cell.id, edge.label)
            if sec.label != 'Soma':
                sec.parentx = edge.parentConnect
                sec.parentID = edge.parentID
            sec.set_3d_geometry(edge.edgePts, edge.diameterList)
            self.cell.sections.append(sec)
            if sec.label == 'Soma':
                self.cell.soma = sec


        # second loop: create structures dict and connectivity
        # between sections
        for sec in self.cell.sections:
            if sec.label != 'Soma':
                sec.parent = self.cell.sections[sec.parentID]
            if sec.label not in self.cell.structures:
                self.cell.structures[sec.label] = [sec]
            else:
                self.cell.structures[sec.label].append(sec)

    def get_cell(self):
        '''Returns cell if it is set up

        Raises:
            RuntimeError: If cell is not set up.

        Returns:
            :py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell`: Cell object.
        '''
        if self.cell is None:
            raise RuntimeError(
                'Trying to access cell before morphology has been loaded')
        return self.cell
