'''
Created on Mar 30, 2012

@author: regger
'''
import numpy as np
#import reader
#import writer
#import cell_parser


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
#        seed = 1234567890
#        self.ranGen = np.random.RandomState(seed)

    def map_synapse_realization(self):
        '''
        maps previously created synapse realization onto neuron
        morphology. self.synDist has to be dict with synapse types as
        keywords and list of tuples (sectionID, sectionx) coding
        the synapse location on the specific sections.
        '''
        sections = self.cell.sections
        synDist = self.synDist
        for synType in list(synDist.keys()):
            for syn in synDist[synType]:
                sectionID, sectionx = syn
                #                find pt ID of point closest to sectionx
                #                better do it approximately than rely on
                #                exact match of floating point numbers...
                closestPtID = 0
                mindx = abs(sectionx - sections[sectionID].relPts[0])
                for i in range(1, sections[sectionID].nrOfPts):
                    tmpdx = abs(sectionx - sections[sectionID].relPts[i])
                    if tmpdx < mindx:
                        mindx = tmpdx
                        closestPtID = i
                self.cell.add_synapse(sectionID, closestPtID, sectionx, synType)

    def map_pruned_synapse_realization(self):
        '''
        maps previously created synapse realization onto neuron
        morphology. self.synDist has to be dict with synapse types as
        keywords and list of tuples (sectionID, sectionx, pruned) coding
        the synapse location on the specific sections and anatomical pruning
        status of these synapses.
        '''
        sections = self.cell.sections
        synDist = self.synDist
        for synType in list(synDist.keys()):
            for syn in synDist[synType]:
                sectionID, sectionx, pruned = syn
                #                find pt ID of point closest to sectionx
                #                better do it approximately than rely on
                #                exact match of floating point numbers...
                closestPtID = 0
                mindx = abs(sectionx - sections[sectionID].relPts[0])
                for i in range(1, sections[sectionID].nrOfPts):
                    tmpdx = abs(sectionx - sections[sectionID].relPts[i])
                    if tmpdx < mindx:
                        mindx = tmpdx
                        closestPtID = i
                newSyn = self.cell.add_synapse(sectionID, closestPtID, sectionx,
                                               synType)
                newSyn.pruned = pruned

    def map_synapse_model_distribution(self, synType, structLabel=None):
        '''
        maps modeled synapse distribution (e.g. normal, uniform, ...)
        onto dendritic tree. synapse distribution synDist 
        has to be iterable of distances of synapses; should be radial
        only, i.e. dendritic branches are selected randomly.
        substructure may be indicated by structLabel.
        '''
        #        for numerical comparison
        eps = 1e-6
        secIDs = []
        if structLabel is not None:
            for i in range(len(self.cell.sections)):
                sec = self.cell.sections[i]
                if sec.label == structLabel:
                    secIDs.append(i)
        else:
            for i in range(len(self.cell.sections)):
                sec = self.cell.sections[i]
                if sec.label == 'Dendrite' or sec.label == 'ApicalDendrite':
                    secIDs.append(i)

#        not very elegant/efficient, but ok for now...
        for synD in self.synDist:
            candidateSections = []
            for ID in secIDs:
                sec = self.cell.sections[ID]
                dist = self._compute_path_length(sec, 0.0)
                if dist + eps <= synD <= dist + sec.L - eps:
                    candidateSections.append(ID)
#            select section
            n = np.random.randint(len(candidateSections))
            sectionID = candidateSections[n]
            #            select point along section
            sec = self.cell.sections[sectionID]
            dist = self._compute_path_length(sec, 0.0)
            synx = (synD - dist) / sec.L
            if synx < 0:
                errstr = 'SynapseMapper: synx < 0 - this should not happen!'
                raise RuntimeError(errstr)
            closestPtID = 0
            mindx = abs(synx - sec.relPts[0])
            for i in range(1, sec.nrOfPts):
                tmpdx = abs(synx - sec.relPts[i])
                if tmpdx < mindx:
                    mindx = tmpdx
                    closestPtID = i
            self.cell.add_synapse(sectionID, closestPtID, synx, synType)

    def create_synapses(self, preType='Generic'):
        '''
        main function; creates instantiation of synapses
        on cell from synapse distribution
        '''
        mesh = self.synDist.mesh
        self._create_voxel_edge_map()
        for vxIndex in list(self.voxelEdgeMap.keys()):
            if self.voxelEdgeMap[vxIndex]:
                nrOfSyn = mesh[vxIndex]
                if self.isDensity:
                    nrOfSyn = np.random.poisson(nrOfSyn)
#                    nrOfSyn = self.ranGen.poisson(nrOfSyn)
                else:
                    nrOfSyn = int(round(nrOfSyn))
                '''choose points at random by shuffling
                all points within the current voxel'''
                candEdges = self.voxelEdgeMap[vxIndex]
                candidatePts = list(np.random.permutation(candEdges))
                #                fix for situation where nrOfSyn > len(candidatePts)!
                while len(candidatePts) < nrOfSyn:
                    candidatePts.append(candEdges[np.random.randint(
                        len(candEdges))])
#                    print 'added another point where nSyn > nPts'
                for n in range(nrOfSyn):
                    edgeID = candidatePts[n][0]
                    edgePtID = candidatePts[n][1]
                    edgex = self.cell.sections[edgeID].relPts[edgePtID]
                    if edgex < 0.0 or edgex > 1.0:
                        raise RuntimeError('Edge x out of range')
                    self.cell.add_synapse(edgeID, edgePtID, edgex, preType)

    def _create_voxel_edge_map(self):
        '''
        fills dictionary voxelEdgeMap with indices of voxels
        and list of pts within that voxel
        '''
        sections = self.cell.sections
        synDist = self.synDist
        voxelEdgeMap = self.voxelEdgeMap

        noSynStructures = ['Soma', 'Axon', 'AIS', 'Myelin', 'Node']
        '''array with all non-zero voxel indices'''
        synVoxels = np.array(synDist.mesh.nonzero()).transpose()
        '''loop over all non-zero voxels'''
        for vxIndex in synVoxels:
            vxIndexT = tuple(vxIndex)
            voxelEdgeMap[vxIndexT] = []
            voxelBBox = synDist.get_voxel_bounds(vxIndex)
            for i in range(len(sections)):
                '''only check section points if section bounding box
                overlaps with voxel bounding box'''
                sec = sections[i]
                #                if sec.label == 'Axon' or sec.label == 'Soma':
                if sec.label in noSynStructures:
                    continue
                if self._intersect_bboxes(voxelBBox, sec.bounds):
                    for n in range(sec.nrOfPts):
                        pt = sec.pts[n]
                        if self._pt_in_box(pt, voxelBBox):
                            voxelEdgeMap[vxIndexT].append((i, n))

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


#def map_synapses(cellFName, synapseFName):
#    synDist = reader.read_scalar_field(synapseFName)
#
#    parser = cell_parser.CellParser(cellFName)
#    parser.spatialgraph_to_cell()
#    synMapper = SynapseMapper(parser.cell, synDist)
#    synMapper.create_synapses()
#
#    return parser.cell

#def main():
#    cellName = '93_CDK080806_marcel_3x3_registered_zZeroBarrel.hoc.am-14678.hoc'
#    synapseFName = 'SynapseCount.14678.am'
#
#    synDist = reader.read_scalar_field(synapseFName)
#    synMapper = SynapseMapper()
#    for i in range(100):
#        print 'Creating synapse instance %s' % i
#        testParser = cell_parser.CellParser(cellName)
#        testParser.spatialgraph_to_cell()
#        synMapper.cell = testParser.get_cell()
#        synMapper.synDist = synDist
#        synMapper.create_synapses()
#        print 'Writing synapse instance %s' % i
#        listOfSynapses = [s.coordinates for s in testParser.cell.synapses['Generic']]
#        landmarkFName = 'random_test_refactor/SynapseInstance_'+str(i)
#        writer.write_landmark_file(landmarkFName, listOfSynapses)
#
#def profile():
##    import cProfile
#    for i in range(10):
#        print 'Creating instance %s' % i
#        cellName = '93_CDK080806_marcel_3x3_registered_zZeroBarrel.hoc.am-14678.hoc'
#        synapseFName = 'SynapseCount.14678.am'
#
#        synDist = reader.read_scalar_field(synapseFName)
#
#        testParser = cell_parser.CellParser(cellName)
#        testParser.spatialgraph_to_cell()
#        synMapper = SynapseMapper(testParser.cell, synDist)
#        synMapper.create_synapses()
##        cProfile.runctx('synMapper.create_synapses()', globals(), locals())
#
#if __name__ == '__main__':
#    main()
##    profile()
