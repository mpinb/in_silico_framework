'''
This module allows to compute synapse density fields from a Post-Synaptic Target (PST) density field and assign synapses to a neuron morphology based on this synapse density field.
The :class:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper` class uses these classes to create synapse realizations.
While the classes in this module can be used in isolation, there are also full pipelines available that use the classes here to map synapses to a neuron morphology.
Consult the module :py:mod:`~singlecell_input_mapper.map_singlecell_inputs` for such a pipeline, or the documentation of :class:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper` for more info on how to use these classes in a pipeline.

Created on Mar 30, 2012

@author: regger
'''
import numpy as np
from .scalar_field import ScalarField
import sys


class SynapseMapper(object):
    '''Assign synapses to neuron morphology from density meshes.

    Poisson sample the synapse distribution mesh and assigns them to a random 
    point on the morphology that lies within the same voxel.
    
    Attributes:
        cell (:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell`):
            The postsynaptic neuron.
        synDist (:class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`):
            Synapse distribution mesh. Can be either a density or a realization 
            (i.e. whole number values per voxel).
        isDensity (bool):
            Set to True if synapse distribution is interpreted as an average density.
            Set to False if synapse distribution is interpreted as an actual realization, 
            and values are whole numbers.
        voxelEdgeMap (dict):
            Dictionary mapping synapse distribution mesh coordinates on list with 
            pairs of indices that correspond to the edge and edgePt ID of all morphology 
            points inside that voxel.
    '''

    def __init__(self, cell=None, synDist=None, isDensity=True):
        '''
        Args:
            cell (:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell`): 
                Neuron morphology to map synapses onto.
            synDist (:class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`): 
                Synapse distribution mesh.
            isDensity (bool): 
                If True, synapse distribution is interpreted as an average density. 
                If False, synapse distribution is interpreted as an actual realization, and values are taken as is.
        '''
        self.cell = cell
        self.synDist = synDist
        self.isDensity = isDensity
        self.voxelEdgeMap = {}


        # seed = int(time.time()) + 2342
        # self.ranGen = np.random.RandomState(seed)

    def create_synapses(self, preType='Generic'):
        '''Creates instantiation of synapses on cell from synapse distribution.
        
        Iterates the cell structures (e.g. "Soma", "Dendrite", "ApicalDendrite").
        For each structure, creates a list of synapses per voxel by poisson sampling the synapse distribution mesh.
        Randomly assignes these synapses to any point on the morphology that lies within the same voxel.
        
        Args:
            preType (str): Type of presynaptic cell. Default is 'Generic'.
        
        Returns:
            list: list of :class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Synapse` objects.
            Also updates the :paramref:`cell` attribute to contain synapses.
        '''
        newSynapses = []
        if not self.voxelEdgeMap:
            self._create_voxel_edge_map()
        for structure in list(self.cell.structures.keys()):
            mesh = self.synDist[structure].mesh
            meshIndices = np.transpose(mesh.nonzero())
            for vxIndex in meshIndices:
                vxIndex = tuple(vxIndex)
                if self.voxelEdgeMap[structure][vxIndex]:
                    nrOfSyn = mesh[vxIndex]
                    
                    # ------- random 1: 
                    # poisson sample the synapse density distribution
                    nrOfSyn = np.random.poisson(nrOfSyn)
                    if not nrOfSyn:
                        continue
                    
                    # ------- random 2: 
                    # choose random synapse target onto the dendrite
                    # within the same voxel.
                    candEdges = self.voxelEdgeMap[structure][vxIndex]
                    candidatePts = list(np.random.permutation(candEdges))
                    # fix for situation where nrOfSyn > len(candidatePts):
                    while len(candidatePts) < nrOfSyn:
                        candidatePts.append(
                            candEdges[np.random.randint(len(candEdges))])
                        
                    # Save synapses
                    for n in range(nrOfSyn):
                        edgeID = candidatePts[n][0]
                        edgePtID = candidatePts[n][1]
                        edgex = self.cell.sections[edgeID].relPts[edgePtID]
                        if edgex < 0.0 or edgex > 1.0:
                            raise RuntimeError('Edge x out of range')
                        newSynapses.append(
                            self.cell.add_synapse(
                                edgeID, 
                                edgePtID, 
                                edgex,
                                preType))
        return newSynapses

    def _create_voxel_edge_map(self):
        '''Fills :paramref:`voxelEdgeMap` with voxel indices, and the section and point indices that the voxel contains.
        
        Only needs to be called once at the beginning.
        '''
        voxelEdgeMap = self.voxelEdgeMap
        for structure in list(self.cell.structures.keys()):
            #            use cell.sections, not cell.structures
            #            this makes synapse placement later easier
            #            because we have the cell.sections ID
            sections = self.cell.sections
            synDist = self.synDist[structure]
            voxelEdgeMap[structure] = {}
            for i in range(synDist.extent[0], synDist.extent[1] + 1):
                for j in range(synDist.extent[2], synDist.extent[3] + 1):
                    for k in range(synDist.extent[4], synDist.extent[5] + 1):
                        ijk = i, j, k
                        voxelEdgeMap[structure][ijk] = []
                        voxelBBox = synDist.get_voxel_bounds(ijk)
                        for section_index in range(len(sections)):
                            '''only check section points if section bounding box
                            overlaps with voxel bounding box'''
                            sec = sections[section_index]
                            if sec.label != structure:
                                continue
                            if self._intersect_bboxes(voxelBBox, sec.bounds):
                                for section_point_index in range(sec.nrOfPts):
                                    pt = sec.pts[section_point_index]
                                    if self._pt_in_box(pt, voxelBBox):
                                        voxelEdgeMap[structure][ijk].append(
                                            (section_index, section_point_index))

    def _intersect_bboxes(self, bbox1, bbox2):
        '''Check if two bounding boxes overlap
        
        Args:   
            bbox1 (tuple): Bounding box of format (minx, maxx, miny, maxy, minz, maxz)
            bbox2 (tuple): Bounding box of format (minx, maxx, miny, maxy, minz, maxz)
            
        Returns:    
            bool: True if bounding boxes overlap, False otherwise.
        '''
        for i in range(3):
            intersect = False
            if bbox1[2 * i] >= bbox2[2 * i] and \
                bbox1[2 * i] <= bbox2[2 * i +1]:
                intersect = True
            elif bbox2[2 * i] >= bbox1[2 * i] and \
                bbox2[2 * i] <= bbox1[2 * i +1]:
                intersect = True
            if bbox1[2 * i + 1] <= bbox2[2 * i + 1] and \
                bbox1[2 * i +1] >= bbox2[2 * i]:
                intersect = True
            elif bbox2[2 * i + 1] <= bbox1[2 * i + 1] and \
                bbox2[2 * i +1] >= bbox1[2 * i]:
                intersect = True
            if not intersect:
                return False
        return True

    def _pt_in_box(self, pt, box):
        """Check if a point is inside a bounding box.
        
        Args:
            pt (array): Point to check.
            box (array): Bounding box to check against. Box is a length-6 array of format (xmin, xmax, ymin, ymax, zmin, zmax).
            
        Returns:
            bool: True if point is inside bounding box, False otherwise."""
        return box[0] <= pt[0] <= box[1] and box[2] <= pt[1] <= box[3] and box[4] <= pt[2] <= box[5]

    def _compute_path_length(self, sec, x):
        '''Calculate the path length betwen the soma and location :paramref:`x` on section :paramref:`sec`
        
        Args:
            sec (:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Section`): Section to calculate path length on.
            x (float): Location on section to calculate path length to.
            
        Returns:
            float: Path length between soma and location :paramref:`x` on section :paramref:`sec`.
        '''
        currentSec = sec
        parentSec = currentSec.parent
        dist = x * currentSec.L
        parentLabel = parentSec.label
        while parentLabel != 'Soma':
            dist += parentSec.L
            currentSec = parentSec
            parentSec = currentSec.parent
            parentLabel = parentSec.label
        return dist


class SynapseDensity(object):
    '''Compute synapse density mesh from a PST density mesh.
    
    Given a PST density mesh, create a 3D mesh of synapse densities for a single postsynaptic neuron using :py:meth:`compute_synapse_density`.
    It is assumed that :py:attr:`~singlecell_input_mapper.singlecell_input_mapper.synapse_maper.SynapseMapper.exPST` and :py:attr:`~singlecell_input_mapper.singlecell_input_mapper.synapse_maper.SynapseMapper.inhPST` have the same bounding box and voxel size.
    This density mesh is used in :class:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseMapper` to assign synapses to the postsynaptic neuron.
    
    This class is used in :class:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper`
    to compute synapse densities per presynaptic cell type for a given postsynaptic cell type and morphology.
    
    :paramref:`exPST` and :paramref:`inhPST` are density meshes for normalizing post-synaptic targets.
    Shown below is an example for such density field: the (25000, 50000, 75000, 100000) isosurfaces of the excitatory 
    PST density field for a rat somatosensory cortex (pia and white matter shown in grey at the top and bottom).
    
    .. figure:: ./_images/exPST_solid_bg.png
    '''
    def __init__(
        self, 
        cell, 
        postCellType, 
        connectionSpreadsheet, 
        exTypes,
        inhTypes, 
        exPST, 
        inhPST):
        '''
        Args:
            cell (:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.Cell`): the postsynaptic neuron
            postCellType (str): cell type of the postsynaptic neuron
            connectionSpreadsheet (dict | DataFrame): spreadsheet containing length/surface area PST densities.
            exTypes (list): list of strings defining excitatory cell types.
            inhTypes (list): list of strings defining inhibitory cell types.
            exPST (:class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`): normalization PST for connections with presynaptic excitatory cell types.
            inhPST (:class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`): normalization PST for connections with presynaptic inhibitory cell types.
            
        Attributes:
            cellPST (dict): 
                Nested dictionary containing the 3D length/surface area density of the postsynaptic neuron.
                See :py:meth:`~SynapseDensity.compute_cell_PST` for details.
        '''
        self.cell = cell
        self.postCellType = postCellType
        self.connectionSpreadsheet = connectionSpreadsheet
        self.exTypes = exTypes
        self.inhTypes = inhTypes
        self.exPST = exPST
        self.inhPST = inhPST
        self.cellPST = {}

    def compute_synapse_density(self, boutonDensity, preCellType):
        '''Compute the density of synapses of a given presynaptic celltype onto the postsynaptic neuron.
        
        Calculates the density field of PSTs of a given post-synaptic morphology using :py:meth:`~SynapseDensity.compute_cell_PST`.
        The density of synapses at each voxel in the density field is computed to be the 
        postsynaptic cell's PST density * presynaptic bouton density / normalization PST density.
        
        This method is used in :class:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper`'s 
        :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.network_embedding.NetworkMapper._precompute_anatomical_area_celltype_synapse_densities`.
        
        Args:
            boutonDensity (:class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`):
                Density of presynaptic boutons.
            preCellType (str):
                Presynaptic cell type.
                
        Returns:
            dict: Dictionary of synapse densities for each structure of the postsynaptic neuron.
            If bouton density and cell PST don't overlap, or synapse density == 0 everywhere, returns None.
        '''
        if not self.cellPST:
            # Compute density fields for postsynaptic targets
            self.compute_cell_PST()

        if preCellType in self.exTypes:
            normPSTDensity = self.exPST
            cellPSTDensity = self.cellPST['EXC']
        elif preCellType in self.inhTypes:
            normPSTDensity = self.inhPST
            cellPSTDensity = self.cellPST['INH']
        else:
            errstr = 'Invalid presynaptic cell type: %s' % preCellType
            raise RuntimeError(errstr)

        synapseDensity = {}
        for structure in list(cellPSTDensity.keys()):
            cellMeshShape = cellPSTDensity[structure].mesh.shape
            cellOrigin = cellPSTDensity[structure].origin
            cellExtent = cellPSTDensity[structure].extent
            cellSpacing = cellPSTDensity[structure].spacing
            cellBoundingBox = cellPSTDensity[structure].boundingBox

            if not self._intersect_bboxes(
                boutonDensity.boundingBox,
                cellBoundingBox
                ):
                return None

            synapseMesh = np.zeros(shape=cellMeshShape)
            synapseDensity[structure] = ScalarField(
                synapseMesh, 
                cellOrigin, 
                cellExtent, 
                cellSpacing,
                cellBoundingBox)
            
            x_start, x_end, y_start, y_end, z_start, z_end = synapseDensity[structure].extent
            for i in range(x_start, x_end + 1):
                for j in range(y_start, y_end + 1):
                    for k in range(z_start, z_end + 1):
                        ijk = i, j, k
                        voxelCenter = synapseDensity[structure].get_voxel_center(ijk)
                        boutons = boutonDensity.get_scalar(voxelCenter)
                        normPST = normPSTDensity.get_scalar(voxelCenter)
                        cellPST = cellPSTDensity[structure].mesh[ijk]
                        if (
                            boutons is not None and 
                            normPST is not None and 
                            normPST > 0.0
                            ):
                            synapseDensity[structure].mesh[ijk] = \
                                boutons * cellPST / normPST

        for structure in list(synapseDensity.keys()):
            keep = False
            if synapseDensity[structure].mesh.nonzero():
                keep = True
        if not keep:
            return None
        return synapseDensity

    def compute_cell_PST(self):
        '''Compute 3D length/surface area density of the postsynaptic targets in the mesh.
        
        Called once to compute 3D length/surface area densities and combine them with length/surface area PST densities to yield connection-specific 3D PST density of the postsynaptic neuron.
        Creates a mesh for each structure of the postsynaptic neuron.
        Calculates the length and surface area density of each structure with :py:meth:`~SynapseDensity._compute_length_surface_area_density`.
        Multiplies the length and area with PST densities per length/area according to the connection spreadsheet :py:attr:`~SynapseDensity.connectionSpreadsheet`, and adds them together.
        This is PST density is normalized in :py:meth:`~SynapseDensity.compute_synapse_density` to obtain synapse densities.
        
        Returns:
            None. 
            Fills the scalar fields in place. 
            :py:attr:`~SynapseDensity.cellPST` is a nested dictionary of the form:
            {'EXC': {'structure_1': :class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`, 'structure_2': ..., ...} 'INH': ...}.
        
        Todo:
            Currently, structures are hardcoded for L5PTs. This method can be extended to accept a mapping
            between the connection spreadsheet column names and cell structures.
        
        Example:
        
        >>> synapseDensity.compute_cell_PST()
        >>> synapseDensity.cellPST['EXC']['Soma'].mesh  # spans the entire bounding box
        array([[[ 0.        ,  0.        ,  0.        ,  0.        ],
                ...,
                [ 0.        ,  0.        ,  0.        ,  0.        ]]])
        >>> synapseDensity.cellPST
        {
            'EXC': {
                'Soma': <singlecell_input_mapper.scalar_field.ScalarField object at 0x7f7f3c0b3b90>, 
                'ApicalDendrite': <singlecell_input_mapper.scalar_field.ScalarField object at 0x7f7f3c0b3c10>, 
                'Dendrite': <singlecell_input_mapper.scalar_field.ScalarField object at 0x7f7f3c0b3c50>
                }, 
            'INH': {
                'Soma': <singlecell_input_mapper.scalar_field.ScalarField object at 0x7f7f3c0b3c90>, 
                'ApicalDendrite': <singlecell_input_mapper.scalar_field.ScalarField object at 0x7f7f3c0b3cd0>, 
                'Dendrite': <singlecell_input_mapper.scalar_field.ScalarField object at 0x7f7f3c0b3d10>}
                }
        '''
        cellMesh, cellOrigin, cellExtent, cellSpacing, cellBoundingBox = \
            self._compute_cell_density_grid()
        cellLengthDensities = {}
        cellSurfaceAreaDensities = {}
        for structure in list(self.cell.structures.keys()):
            cellLengthDensities[structure] = ScalarField(
                cellMesh, cellOrigin, cellExtent, cellSpacing, cellBoundingBox)
            cellSurfaceAreaDensities[structure] = ScalarField(
                cellMesh, cellOrigin, cellExtent, cellSpacing, cellBoundingBox)
        # Where the cell intersects the mesh
        self._compute_length_surface_area_density(
            cellLengthDensities,
            cellSurfaceAreaDensities,
            likeAmira=1)

        #=======================================================================
        # for testing only:
        #=======================================================================
        #        self.cellPST = cellLengthDensities

        self.cellPST['EXC'] = {}
        self.cellPST['INH'] = {}
        for structure in list(self.cell.structures.keys()):
            self.cellPST['EXC'][structure] = ScalarField(
                cellMesh, cellOrigin, cellExtent, cellSpacing, cellBoundingBox)
            self.cellPST['INH'][structure] = ScalarField(
                cellMesh, cellOrigin, cellExtent, cellSpacing, cellBoundingBox)
            exConstants = self.connectionSpreadsheet['EXC'][self.postCellType]
            inhConstants = self.connectionSpreadsheet['INH'][self.postCellType]

            if structure == 'Soma':
                self.cellPST['EXC'][structure].mesh += exConstants[
                    'SOMA_LENGTH'] * cellLengthDensities[structure].mesh
                self.cellPST['EXC'][structure].mesh += exConstants[
                    'SOMA_AREA'] * cellSurfaceAreaDensities[structure].mesh
                self.cellPST['INH'][structure].mesh += inhConstants[
                    'SOMA_LENGTH'] * cellLengthDensities[structure].mesh
                self.cellPST['INH'][structure].mesh += inhConstants[
                    'SOMA_AREA'] * cellSurfaceAreaDensities[structure].mesh
            if structure == 'ApicalDendrite':
                self.cellPST['EXC'][structure].mesh += exConstants[
                    'APICAL_LENGTH'] * cellLengthDensities[structure].mesh
                self.cellPST['EXC'][structure].mesh += exConstants[
                    'APICAL_AREA'] * cellSurfaceAreaDensities[structure].mesh
                self.cellPST['INH'][structure].mesh += inhConstants[
                    'APICAL_LENGTH'] * cellLengthDensities[structure].mesh
                self.cellPST['INH'][structure].mesh += inhConstants[
                    'APICAL_AREA'] * cellSurfaceAreaDensities[structure].mesh
            if structure == 'Dendrite':
                self.cellPST['EXC'][structure].mesh += exConstants[
                    'BASAL_LENGTH'] * cellLengthDensities[structure].mesh
                self.cellPST['EXC'][structure].mesh += exConstants[
                    'BASAL_AREA'] * cellSurfaceAreaDensities[structure].mesh
                self.cellPST['INH'][structure].mesh += inhConstants[
                    'BASAL_LENGTH'] * cellLengthDensities[structure].mesh
                self.cellPST['INH'][structure].mesh += inhConstants[
                    'BASAL_AREA'] * cellSurfaceAreaDensities[structure].mesh

    def _compute_length_surface_area_density(
        self,
        lengthDensity,
        surfaceAreaDensity,
        likeAmira=0):
        '''Fills the scalar fields :paramref:`lengthDensity` and :paramref:`surfaceDensity` to contain length and area per structure per voxel.
        
        This method is an implementation of line segment clipping using the 
        Liang-barsky algorithm (http://en.wikipedia.org/wiki/Liang%E2%80%93Barsky_algorithm).
        This makes use of the fact that end points of individual sections are beginning points 
        of connected sections and represented in each section separately.
        This way, sections can be treated separately from each other.
        
        The methods runs in two steps:
        
        1. Compute length between all pairs of points that are located in the same grid cell (vast majority)
        2. Use Liang-Barsky for clipping line segments between remaining points that are not located within same grid cell
        
        Args:
            lengthDensity (dict): 
                dictionary with structure labels as keys (e.g. "Soma", "Dendrite"...) and 
                :class:`~singlecell_input_mapper.singlecell_input_mapper.calar_field.ScalarField` objects as values
            surfaceAreaDensity (dict):
                dictionary with structure labels as keys (e.g. "Soma", "Dendrite"...) and
                :class:`~singlecell_input_mapper.singlecell_input_mapper.calar_field.ScalarField` objects as values
            likeAmira (bool):
                Set to True if the diamlist of each section denotes the radius, rather than the diameter.
                Default is False.
                
        Returns:
            None. Fills the scalar fields in place.
        '''
        print('---------------------------')
        totalLength = 0.0
        for structure in list(lengthDensity.keys()):
            print(
                'Computing 3D length/surface area density of structures with label {:s}'
                .format(structure))
            density1 = lengthDensity[structure]
            density2 = surfaceAreaDensity[structure]
            #===================================================================
            # Two steps:
            # 1. Compute length between all pairs of points that are located
            # in the same grid cell (vast majority)
            # 2. Use Liang-Barsky for clipping line segments between remaining
            # points that are not located within same grid cell
            #===================================================================
            clipSegments = []
            clipSegmentsRadius = []
            for sec in self.cell.structures[structure]:
                for i in range(sec.nrOfPts - 1):
                    pt1 = np.array(sec.pts[i])
                    pt2 = np.array(sec.pts[i + 1])
                    if not likeAmira:
                        r1 = sec.diamList[i] * 0.5
                        r2 = sec.diamList[i + 1] * 0.5
                    # Amira Bug: uses diameter instead of radius
                    # (doesn't matter for end result, but it's affecting
                    # the INH PST density -> need to be consistent...)
                    if likeAmira:
                        r1 = sec.diamList[i]
                        r2 = sec.diamList[i + 1]
                    gridCell1 = density1.get_mesh_coordinates(pt1)
                    gridCell2 = density1.get_mesh_coordinates(pt2)
                    if gridCell1 == gridCell2:
                        diff = pt2 - pt1
                        length = np.sqrt(np.dot(diff, diff))
                        area = self._get_truncated_cone_area(length, r1, r2)
                        density1.mesh[gridCell1] += length
                        density2.mesh[gridCell1] += area
                        totalLength += length
                    else:
                        clipSegments.append((pt1, pt2))
                        clipSegmentsRadius.append((r1, r2))


            # dims = density1.extent[1]+1, density1.extent[3]+1, density1.extent[5]+1
            # nrOfVoxels = dims[0]*dims[1]*dims[2]
            count = 0
            #            print 'Checking %dx%dx%d = %d voxels...' % (dims[0],dims[1],dims[2],nrOfVoxels)
            nrOfSegments = len(clipSegments)
            #            print 'Clipping %d segments...' % (nrOfSegments)
            #            for segment in clipSegments:
            for n in range(len(clipSegments)):
                segment = clipSegments[n]
                segmentRadius = clipSegmentsRadius[n]
                print('{:d} of {:d} done...\r'.format(
                    count, nrOfSegments))  #, end=' ')
                sys.stdout.flush()
                count += 1
                for i in range(density1.extent[0], density1.extent[1] + 1):
                    for j in range(density1.extent[2], density1.extent[3] + 1):
                        for k in range(density1.extent[4],
                                       density1.extent[5] + 1):
                            #                            print '%d of %d done...\r' % (count,nrOfVoxels),
                            #                            sys.stdout.flush()
                            #                            count += 1
                            ijk = i, j, k
                            voxelBounds = density1.get_voxel_bounds(ijk)
                            pt1 = segment[0]
                            pt2 = segment[1]
                            dx_ = pt2 - pt1

                            dx = dx_[0]
                            dy = dx_[1]
                            dz = dx_[2]
                            p1 = -dx
                            p2 = dx
                            p3 = -dy
                            p4 = dy
                            p5 = -dz
                            p6 = dz
                            q1 = pt1[0] - voxelBounds[0]
                            q2 = voxelBounds[1] - pt1[0]
                            q3 = pt1[1] - voxelBounds[2]
                            q4 = voxelBounds[3] - pt1[1]
                            q5 = pt1[2] - voxelBounds[4]
                            q6 = voxelBounds[5] - pt1[2]

                            u1 = 0
                            u2 = 1
                            pq1 = [p1, q1]
                            pq2 = [p2, q2]
                            pq3 = [p3, q3]
                            pq4 = [p4, q4]
                            pq5 = [p5, q5]
                            pq6 = [p6, q6]
                            u1u2 = [u1, u2]
                            if self._clip_u(pq1, u1u2) and self._clip_u(pq2, u1u2)\
                                and self._clip_u(pq3, u1u2) and self._clip_u(pq4, u1u2)\
                                and self._clip_u(pq5, u1u2) and self._clip_u(pq6, u1u2):
                                u1 = u1u2[0]
                                u2 = u1u2[1]
                            else:
                                continue

                            if u2 < u1:
                                continue

                            clipPt1 = pt1 + u1 * dx_
                            clipPt2 = pt1 + u2 * dx_
                            #                            diff = clipPt2 - clipPt1
                            diff = (u2 - u1) * dx_
                            length = np.sqrt(np.dot(diff, diff))
                            r1 = segmentRadius[0]
                            r2 = segmentRadius[1]
                            r1Interpolated = self._interpolate_radius(
                                pt1, pt2, r1, r2, clipPt1)
                            r2Interpolated = self._interpolate_radius(
                                pt1, pt2, r1, r2, clipPt2)
                            area = self._get_truncated_cone_area(
                                length, r1Interpolated, r2Interpolated)
                            density1.mesh[ijk] += length
                            density2.mesh[ijk] += area
                            totalLength += length
        print('Total clipped length = {:f}'.format(totalLength))
        print('---------------------------')

    def _clip_u(self, pq, u1u2):
        '''Liang-Barsky clipping algorithm :cite:`liang1984new` for line segments in 3D.
        
        Used in :py:meth:`~SynapseDensity._compute_length_surface_area_density` to clip line segments to scalar field meshes.
        '''
        p = pq[0]
        q = pq[1]
        u1 = u1u2[0]
        u2 = u1u2[1]
        if p < 0:
            tmp = q / p
            if tmp > u2:
                return False
            elif tmp > u1:
                u1 = tmp
        elif p > 0:
            tmp = q / p
            if tmp < u1:
                return False
            elif tmp < u2:
                u2 = tmp
        elif self._is_zero(p) and q < 0:
            return False
        u1u2[0] = u1
        u1u2[1] = u2
        return True

    def _get_truncated_cone_area(self, height, radius1, radius2):
        """Calculate the are of a truncated cone.
        
        Used in :py:meth:`~SynapseDensity._compute_length_surface_area_density` to calculate the area of clipped neurites."""
        deltaR = radius2 - radius1
        slantedHeight = np.sqrt(height * height + deltaR * deltaR)
        return np.pi * (radius1 + radius2) * slantedHeight

    def _interpolate_radius(self, p0, p1, radius0, radius1, targetPt):
        """Interpolate the radius of a segment between two points.
        
        Args:
            p0 (array): Start point of the segment.
            p1 (array): End point of the segment.
            radius0 (float): Radius at the start point.
            radius1 (float): Radius at the end point.
            targetPt (array): Point at which to interpolate the radius.
            
        Returns:
            float: Interpolated radius at :paramref:`targetPt`."""
        totalLength = np.sqrt(np.dot(p1 - p0, p1 - p0))
        if -1e-4 < totalLength < 1e-4:
            return 0.5 * (radius0 + radius1)
        p0TargetLength = np.sqrt(np.dot(targetPt - p0, targetPt - p0))
        alpha = p0TargetLength / totalLength
        return alpha * radius1 + (1.0 - alpha) * radius0

    def _compute_cell_density_grid(self):
        """Create an empty mesh for the postsynaptic neuron to match the mesh of the synapse distribution.
        
        Returns:
            tuple: Tuple containing:
            
                - cellMesh (array): Empty mesh for the postsynaptic neuron.
                - cellOrigin (tuple): Origin of the mesh.
                - cellExtent (tuple): Extent of the mesh.
                - cellSpacing (tuple): Spacing of the mesh (dx, dy, dz).
                - cellBoundingBox (tuple): Bounding box of the mesh (minx, maxx, miny, maxy, minz, maxz).
        """
        cellBounds = self.cell.get_bounding_box()
        #        print 'Cell bounding box:'
        #        print cellBounds
        iMin = self.exPST.extent[1]
        iMax = self.exPST.extent[0]
        jMin = self.exPST.extent[3]
        jMax = self.exPST.extent[2]
        kMin = self.exPST.extent[5]
        kMax = self.exPST.extent[4]
        for i in range(self.exPST.extent[0], self.exPST.extent[1] + 1):
            for j in range(self.exPST.extent[2], self.exPST.extent[3] + 1):
                for k in range(self.exPST.extent[4], self.exPST.extent[5] + 1):
                    ijk = i, j, k
                    voxelBounds = self.exPST.get_voxel_bounds(ijk)
                    if not self._intersect_bboxes(cellBounds, voxelBounds):
                        continue
                    if i < iMin:
                        iMin = i
                    if i > iMax:
                        iMax = i
                    if j < jMin:
                        jMin = j
                    if j > jMax:
                        jMax = j
                    if k < kMin:
                        kMin = k
                    if k > kMax:
                        kMax = k

        cellExtent = 0, iMax - iMin, 0, jMax - jMin, 0, kMax - kMin
        cellDims = cellExtent[1] + 1, cellExtent[3] + 1, cellExtent[5] + 1
        dx = self.exPST.spacing[0]
        dy = self.exPST.spacing[1]
        dz = self.exPST.spacing[2]
        cellSpacing = dx, dy, dz
        xMin = self.exPST.origin[0] + iMin * dx
        yMin = self.exPST.origin[1] + jMin * dy
        zMin = self.exPST.origin[2] + kMin * dz
        xMax = self.exPST.origin[0] + (iMax + 1) * dx
        yMax = self.exPST.origin[1] + (jMax + 1) * dy
        zMax = self.exPST.origin[2] + (kMax + 1) * dz
        cellOrigin = xMin, yMin, zMin
        cellBoundingBox = xMin, xMax, yMin, yMax, zMin, zMax
        cellMesh = np.zeros(shape=cellDims)
        #        print 'Cell structures grid'
        #        print 'Origin:'
        #        print cellOrigin
        #        print 'Bounding box:'
        #        print cellBoundingBox
        #        print 'Extent:'
        #        print cellExtent
        #        print 'Dims:'
        #        print cellDims

        return cellMesh, cellOrigin, cellExtent, cellSpacing, cellBoundingBox

    def _is_zero(self, number):
        """Check if a number is close to zero (tolerance of 1e-10)
        
        Args:
            number (float): Number to check."""
        eps = 1e-10
        return number < eps and number > -eps

    def _intersect_bboxes(self, bbox1, bbox2):
        '''Check if two bounding boxes overlap
        
        Args:
            bbox1 (tuple): Bounding box of the first object (minx, maxx, miny, maxy, minz, maxz).
            bbox2 (tuple): Bounding box of the second object (minx, maxx, miny, maxy, minz, maxz).
            
        Returns:
            bool: True if the bounding boxes overlap, False otherwise.
        '''
        for i in range(3):
            intersect = False
            if bbox1[2 * i] >= bbox2[2 * i] and \
                bbox1[2 * i] <= bbox2[2 * i + 1]:
                intersect = True
            elif bbox2[2 * i] >= bbox1[2 * i] and \
                bbox2[2 * i] <= bbox1[2 * i + 1]:
                intersect = True
            if bbox1[2 * i + 1] <= bbox2[2 * i + 1] and \
                bbox1[2 * i + 1] >= bbox2[2 * i]:
                intersect = True
            elif bbox2[2 * i + 1] <= bbox1[2 * i + 1] and\
                bbox2[2 * i + 1] >= bbox1[2 * i]:
                intersect = True
            if not intersect:
                return False

        return True
