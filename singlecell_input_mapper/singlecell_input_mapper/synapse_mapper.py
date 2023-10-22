'''
Created on Mar 30, 2012

@author: regger
'''
import numpy as np
from .scalar_field import ScalarField
import sys


class SynapseMapper(object):
    '''
    SynapseMapper assigns synapses to neuron morphology
    self.cell is neuron SpatialGraph
    self.synDist is average synapse distribution (3D scalar field)
    self.isDensity: True - synapse distribution interpreted as avg
        density; actual number of synapses assigned is drawn from a 
        Poisson distribution
        False - synapse distribution interpreted as actual number of
        synapses per voxel and directly assigned
    self.voxelEdgeMap: dictionary mapping synapse distribution mesh
        coordinates on list with pairs of indices that correspond
        to the edge and edgePt ID of all morphology points inside that voxel
    '''

    def __init__(self, cell=None, synDist=None, isDensity=True):
        '''
        synapses are mapped onto this cell
        self.cell = cell
        
        synapse distribution
        self.synDist = synDist
        
        flag: 1 - distribution is density; 0 - distribution is realization
        self.isDensity = isDensity
        
        stores edge/voxel correspondence for mapping
        self.voxelEdgeMap = {}
        '''
        self.cell = cell
        self.synDist = synDist
        self.isDensity = isDensity
        self.voxelEdgeMap = {}


#        seed = int(time.time()) + 2342
#        self.ranGen = np.random.RandomState(seed)

    def create_synapses(self, preType='Generic'):
        '''
        main function; creates instantiation of synapses
        on cell from synapse distribution
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
                    nrOfSyn = np.random.poisson(nrOfSyn)
                    if not nrOfSyn:
                        continue
                    '''choose points at random by shuffling
                    all points within the current voxel'''
                    candEdges = self.voxelEdgeMap[structure][vxIndex]
                    candidatePts = list(np.random.permutation(candEdges))
                    #                fix for situation where nrOfSyn > len(candidatePts):
                    while len(candidatePts) < nrOfSyn:
                        candidatePts.append(candEdges[np.random.randint(
                            len(candEdges))])
                    for n in range(nrOfSyn):
                        edgeID = candidatePts[n][0]
                        edgePtID = candidatePts[n][1]
                        edgex = self.cell.sections[edgeID].relPts[edgePtID]
                        if edgex < 0.0 or edgex > 1.0:
                            raise RuntimeError('Edge x out of range')
                        newSynapses.append(
                            self.cell.add_synapse(edgeID, edgePtID, edgex,
                                                  preType))
        return newSynapses

    def _create_voxel_edge_map(self):
        '''
        fills dictionary voxelEdgeMap with indices of voxels
        and list of pts within that voxel
        Only needs to be called once at the beginning
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
                        for l in range(len(sections)):
                            '''only check section points if section bounding box
                            overlaps with voxel bounding box'''
                            sec = sections[l]
                            if sec.label != structure:
                                continue
                            if self._intersect_bboxes(voxelBBox, sec.bounds):
                                for n in range(sec.nrOfPts):
                                    pt = sec.pts[n]
                                    if self._pt_in_box(pt, voxelBBox):
                                        voxelEdgeMap[structure][ijk].append(
                                            (l, n))

    def _intersect_bboxes(self, bbox1, bbox2):
        '''
        check if two bounding boxes overlap
        '''
        for i in range(3):
            intersect = False
            if bbox1[2 * i] >= bbox2[2 * i] and bbox1[2 * i] <= bbox2[2 * i +
                                                                      1]:
                intersect = True
            elif bbox2[2 * i] >= bbox1[2 * i] and bbox2[2 * i] <= bbox1[2 * i +
                                                                        1]:
                intersect = True
            if bbox1[2 * i + 1] <= bbox2[2 * i + 1] and bbox1[2 * i +
                                                              1] >= bbox2[2 *
                                                                          i]:
                intersect = True
            elif bbox2[2 * i + 1] <= bbox1[2 * i + 1] and bbox2[2 * i +
                                                                1] >= bbox1[2 *
                                                                            i]:
                intersect = True
            if not intersect:
                return False

        return True

    def _pt_in_box(self, pt, box):
        return box[0] <= pt[0] <= box[1] and box[2] <= pt[1] <= box[3] and box[
            4] <= pt[2] <= box[5]

    def _compute_path_length(self, sec, x):
        '''path length to soma from location x on section sec'''
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
    '''
    Synapse density computation for one postsynaptic neuron
    and arbitrary presynaptic bouton and other postsynaptic
    PST densities
    '''

    def __init__(self, cell, postCellType, connectionSpreadsheet, exTypes,
                 inhTypes, exPST, inhPST):
        '''
        postsynaptic neuron
        self.cell = cell
        
        spreadsheet containing length/surface area PST densities
        self.connectionSpreadsheet = connectionSpreadsheet
        
        defined excitatory cell types
        self.exTypes = exTypes
        
        defined inhibitory cell types
        self.inhTypes = inhTypes
        
        normalization PST for connections with
        presynaptic excitatory cell types
        self.exPST = exPST
        
        normalization PST for connections with
        presynaptic inhibitory cell types
        self.inhPST = inhPST
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
        '''
        main interface for computing synapses originating
        from presynaptic bouton density of given cell type
        If bouton density and cell PST don't overlap
        or synapse density == 0 everywhere, return None
        '''
        if not self.cellPST:
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

            if not self._intersect_bboxes(boutonDensity.boundingBox,
                                          cellBoundingBox):
                return None

            synapseMesh = np.zeros(shape=cellMeshShape)
            synapseDensity[structure] = ScalarField(synapseMesh, cellOrigin,
                                                    cellExtent, cellSpacing,
                                                    cellBoundingBox)

            for i in range(synapseDensity[structure].extent[0],
                           synapseDensity[structure].extent[1] + 1):
                for j in range(synapseDensity[structure].extent[2],
                               synapseDensity[structure].extent[3] + 1):
                    for k in range(synapseDensity[structure].extent[4],
                                   synapseDensity[structure].extent[5] + 1):
                        ijk = i, j, k
                        voxelCenter = synapseDensity[
                            structure].get_voxel_center(ijk)
                        boutons = boutonDensity.get_scalar(voxelCenter)
                        normPST = normPSTDensity.get_scalar(voxelCenter)
                        cellPST = cellPSTDensity[structure].mesh[ijk]
                        if boutons is not None and normPST is not None and normPST > 0.0:
                            synapseDensity[structure].mesh[
                                ijk] = boutons * cellPST / normPST

        for structure in list(synapseDensity.keys()):
            keep = False
            if synapseDensity[structure].mesh.nonzero():
                keep = True
        if not keep:
            return None
        return synapseDensity

    def compute_cell_PST(self):
        '''
        called once to compute 3D length/surface area
        densities and combine them with length/surface area
        PST densities to yield connection-specific 3D PST
        density of the postsynaptic neuron
        '''
        cellMesh, cellOrigin, cellExtent, cellSpacing, cellBoundingBox = self._compute_cell_density_grid(
        )
        cellLengthDensities = {}
        cellSurfaceAreaDensities = {}
        for structure in list(self.cell.structures.keys()):
            cellLengthDensities[structure] = ScalarField(
                cellMesh, cellOrigin, cellExtent, cellSpacing, cellBoundingBox)
            cellSurfaceAreaDensities[structure] = ScalarField(
                cellMesh, cellOrigin, cellExtent, cellSpacing, cellBoundingBox)
        self._compute_length_surface_area_density(cellLengthDensities,
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

    def _compute_length_surface_area_density(self,
                                             lengthDensity,
                                             surfaceAreaDensity,
                                             likeAmira=0):
        '''
        Implementation of clipping of line segments
        by 3D voxels given by lengthDensity[structure]
        (using Liang-Barsky line clipping algorithm,
        http://en.wikipedia.org/wiki/Liang%E2%80%93Barsky_algorithm).
        Make use of the fact that end points of
        individual sections are beginning points of
        connected sections and represented in each
        section separately -> sections can be treated
        independently of another
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
#                    Amira Bug: uses diameter instead of radius
#                    (doesn't matter for end result, but it's affecting
#                    the INH PST density -> need to be consistent...)
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


#            dims = density1.extent[1]+1, density1.extent[3]+1, density1.extent[5]+1
#            nrOfVoxels = dims[0]*dims[1]*dims[2]
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
        '''
        Liang-Barsky clipping
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
        deltaR = radius2 - radius1
        slantedHeight = np.sqrt(height * height + deltaR * deltaR)
        return np.pi * (radius1 + radius2) * slantedHeight

    def _interpolate_radius(self, p0, p1, radius0, radius1, targetPt):
        totalLength = np.sqrt(np.dot(p1 - p0, p1 - p0))
        if -1e-4 < totalLength < 1e-4:
            return 0.5 * (radius0 + radius1)
        p0TargetLength = np.sqrt(np.dot(targetPt - p0, targetPt - p0))
        alpha = p0TargetLength / totalLength
        return alpha * radius1 + (1.0 - alpha) * radius0

    def _compute_cell_density_grid(self):
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
        eps = 1e-10
        return number < eps and number > -eps

    def _intersect_bboxes(self, bbox1, bbox2):
        '''
        check if two bounding boxes overlap
        '''
        for i in range(3):
            intersect = False
            if bbox1[2 * i] >= bbox2[2 * i] and bbox1[2 * i] <= bbox2[2 * i +
                                                                      1]:
                intersect = True
            elif bbox2[2 * i] >= bbox1[2 * i] and bbox2[2 * i] <= bbox1[2 * i +
                                                                        1]:
                intersect = True
            if bbox1[2 * i + 1] <= bbox2[2 * i + 1] and bbox1[2 * i +
                                                              1] >= bbox2[2 *
                                                                          i]:
                intersect = True
            elif bbox2[2 * i + 1] <= bbox1[2 * i + 1] and bbox2[2 * i +
                                                                1] >= bbox1[2 *
                                                                            i]:
                intersect = True
            if not intersect:
                return False

        return True
