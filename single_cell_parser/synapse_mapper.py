'''Basic synapse mapper to assign synapses to a neuron morphology, based on an existing synapse distribution.

For more fine-grained control over the creation of synapse distributions onto a morphology, 
please refer to the :py:mod:`singlecell_input_mapper.singlecell_input_mapper` package instead.
'''
import numpy as np
#import reader
#import writer
#import cell_parser

__author__ = 'Robert Egger'
__date__ = '2012-03-30'

class SynapseMapper(object):
    '''Assign synapses to a neuron morphology based on an existing synapse distribution.
    
    For more fine-grained control over the creation of synapse distributions onto a morphology, 
    please refer to the :py:mod:`singlecell_input_mapper.singlecell_input_mapper` package instead.

    The synapse distribution can be:

    - a previously created synapse realization in dictionary form 
      (see the :ref:`syn_file_format` file type and :py:meth:`~single_cell_parser.reader.read_synapse_realization` for more info)
    - a :py:class:`~single_cell_parser.scalar_field.ScalarField` of synapse densities, in which case the synapses are mapped
      in the same way as in :py:meth:`~single_cell_parser.synapse_mapper.SynapseMapper.create_synapses`.
    - a list of synapse distances.
    
    See also:
        :py:mod:`singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseMapper` for creating
        network realizations constrained with empirical data.
    
    Attributes:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell to map synapses onto.
        synDist (dict | :py:class:`single_cell_parser.scalar_field.ScalarField` | list): 
            The synapse distribution to map onto the cell.
        isDensity (bool): Flag for distribution type: (1) density or (0) realization.
        voxelEdgeMap (dict): Dictionary that maps voxel edges to (sectionID, pointID) pairs.
    '''
    def __init__(self, cell=None, synDist=None, isDensity=True):
        '''
        :paramref:`synDist` can be read from a :ref:`syn_file_format` file using :py:meth:`~single_cell_parser.reader.read_synapse_realization`.

        Args:
            cell (:py:class:`~single_cell_parser.cell.Cell`): The cell to map synapses onto.
            synDist (dict | :py:class:`single_cell_parser.scalar_field.ScalarField`): 
                Either a previously created synapse realization in dictionary form (see the :ref:`syn_file_format` file type and :py:meth:`~single_cell_parser.reader.read_synapse_realization` for more info)
                or a :py:class:`~single_cell_parser.scalar_field.ScalarField` of synapse densities.
            isDensity (bool): 
                If True, then the synapse distribution is interpreted as an average density, and the actual number of synapses that will be assigned is drawn from a Poisson distribution. 
                If False, then the synapse distribution :paramref:`synDist` is interpreted as the actual number of synapses per voxel. 
        
        '''
        self.cell = cell
        self.synDist = synDist
        self.isDensity = isDensity
        self.voxelEdgeMap = {}
        # seed = 1234567890
        # self.ranGen = np.random.RandomState(seed)

    def map_synapse_realization(self):
        '''Maps previously created synapse realization onto neuron morphology. 
        
        In this case, :paramref:`synDist` has to be a dictionary with synapse types as
        keys and list of tuples (sectionID, sectionx) coding the synapse location on the specific sections as values.

        See also:

        - :py:meth:`~single_cell_parser.reader.read_synapse_realization`
        - The :ref:`syn_file_format` file type.
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
        '''Maps previously created synapse realization onto neuron
        morphology. 
        
        In this case, :paramref:`synDist` has to be dict with synapse types as
        keywords and list of tuples (sectionID, sectionx, pruned) coding
        the synapse location on the specific sections and anatomical pruning
        status of these synapses.

        See also:

        - :py:meth:`~single_cell_parser.reader.read_pruned_synapse_realization`
        - The :ref:`syn_file_format` file type.
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
        '''Maps modeled synapse distribution (e.g. normal, uniform, ...) onto dendritic tree. 

        For each distance in :paramref:`synDist`, a synapse is placed on a random dendritic branch at that distance from the soma.
        In this case, :paramref:`synDist` has to be iterable of distances of synapses.
        Substructure may be indicated by structLabel.

        Args:
            synType (str): The type of synapse to be placed.
            structLabel (str): The label of the substructure to place synapses on. Default: None (all dendritic sections).
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

        # not very elegant/efficient, but ok for now...
        for synD in self.synDist:
            # all cell sections that contain a distance of synD
            candidateSections = []  
            for ID in secIDs:
                sec = self.cell.sections[ID]
                dist = self._compute_path_length(sec, 0.0)
                if dist + eps <= synD <= dist + sec.L - eps:
                    candidateSections.append(ID)
            
            # select section
            n = np.random.randint(len(candidateSections))
            sectionID = candidateSections[n]
            # select point along section
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
        '''Map synapses onto a morphology based on a synapse distribution.

        In this case, :paramref:`synDist` has to be a :py:class:`~single_cell_parser.scalar_field.ScalarField` of synapse densities.

        This method is nearly identical to :py:mod:`singlecell_inputmapper`'s
        :py:meth:`~singlecell_input_mapper.singlecell_input_mapper.synapse_mapper.SynapseMapper.create_synapses`, 
        but with the following differences:

        - the synapse density is not drawn from a Poisson distribution if :paramref:`isDensity` is False.
        - the synapses are not assigned on a per-structure basis (e.g. separate for soma, dendrite, axon ...)

        It is added here for completeness, in case you need a singular, quick network realization.
        For a specialized network realization with more fine-grained control, use the :py:mod:`singlecell_inputmapper.singlecell_input_mapper` package instead.

        Args:
            preType (str): The type of presynaptic cell. Default: 'Generic'.
        '''
        mesh = self.synDist.mesh
        self._create_voxel_edge_map()
        for vxIndex in list(self.voxelEdgeMap.keys()):
            if self.voxelEdgeMap[vxIndex]:
                nrOfSyn = mesh[vxIndex]
                if self.isDensity:
                    nrOfSyn = np.random.poisson(nrOfSyn)
                    # nrOfSyn = self.ranGen.poisson(nrOfSyn)
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
                    # print 'added another point where nSyn > nPts'
                for n in range(nrOfSyn):
                    edgeID = candidatePts[n][0]
                    edgePtID = candidatePts[n][1]
                    edgex = self.cell.sections[edgeID].relPts[edgePtID]
                    if edgex < 0.0 or edgex > 1.0:
                        raise RuntimeError('Edge x out of range')
                    self.cell.add_synapse(edgeID, edgePtID, edgex, preType)

    def _create_voxel_edge_map(self):
        '''Fills dictionary :paramref:`voxelEdgeMap` with indices of voxels pts within that voxel

        The dictionary is structured as follows:
        
        - keys: voxel indices
        - values: list of (sectionID, pointID) pairs of points within that voxel
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
        '''Check if two bounding boxes overlap
        
        Args:
            bbox1 (tuple): Bounding box of the first object (minx, maxx, miny, maxy, minz, maxz).
            bbox2 (tuple): Bounding box of the second object (minx, maxx, miny, maxy, minz, maxz).
            
        Returns:
            bool: True if the bounding boxes overlap, False otherwise.
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
        """Check if a point is within a bounding box
        
        Args:
            pt (tuple): The point to check.
            box (tuple): The bounding box (minx, maxx, miny, maxy, minz, maxz).
        
        Returns:
            bool: True if the point is within the bounding box, False otherwise.
        """
        return box[0] <= pt[0] <= box[1] and box[2] <= pt[1] <= box[3] and box[
            4] <= pt[2] <= box[5]

    def _compute_path_length(self, sec, x):
        '''Compute the path length to soma from location :paramref:`x` on section :paramref:`sec`
        
        Args:
            sec (:py:class:`~single_cell_parser.section.Section`): The section to compute the path length on.
            x (float): The relative coordinate along the section.

        Returns:
            float: The path length to the soma.
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
