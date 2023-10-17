'''
Created on Mar 8, 2012

@author: regger
'''

import numpy as np
from . import scalar_field
from model_data_base.mdbopen import mdbopen
import logging
log = logging.getLogger("ISF").getChild(__name__)

class Edge(object):
    '''
    Edge object contains list of points,
    diameter at each point, label,
    string hocLabel, parentID
    Used during reading of hoc files
    '''
    
    def is_valid(self):
        if not self.label:
            self.valid = False
            return False
        if not self.hocLabel:
            self.valid = False
            return False
        if not self.edgePts:
            self.valid = False
            return False
        self.valid = True
        return True
    
def read_hoc_file(fname=''):
    if not fname.endswith('.hoc') and not fname.endswith('.HOC'):
        raise IOError('Input file is not a .hoc file!')
    
    with mdbopen(fname, 'r') as neuronFile:
        log.info("Reading hoc file %s" % fname)
#        cell = co.Cell()
#        simply store list of edges
#        cell is parsed in CellParser
        cell = []
        
        '''
        set up all temporary data structures
        that hold the cell morphology
        before turning it into a Cell
        '''
        tmpEdgePtList = []
        tmpEdgePtCntList = []
        tmpDiamList = []
        tmpLabelList = []
        tmpHocLabelList = []
        segmentInsertOrder = {}
        segmentParentMap = {}
        segmentConMap = {}
        readPts = edgePtCnt = insertCnt = 0
        
        for line in neuronFile:
            if line:
                '''skip comments'''
                if '/*' in line and '*/' in line:
                    continue
#                    '''ignore daVinci registration'''
#                    if '/* EOF */' in line:
#                        break
                
                '''read pts belonging to current segment'''
                if readPts:
                    if 'Spine' in line:
                        continue
                    if 'pt3dadd' in line:
                        ptStr = line.partition('(')[2].partition(')')[0]
                        ptStrList = ptStr.split(',')
                        tmpEdgePtList.append([float(ptStrList[0]), float(ptStrList[1]), float(ptStrList[2])])
                        tmpDiamList.append(float(ptStrList[3]))
                        edgePtCnt += 1
                        continue
                    elif 'pt3dadd' not in line and edgePtCnt:
                        readPts = 0
                        tmpEdgePtCntList.append(edgePtCnt)
                        edgePtCnt = 0
                
                '''determine type of section'''
                '''and insert section name'''
                if 'soma' in line and 'create' in line:
                    tmpLabelList.append('Soma')
                    readPts = 1
                    edgePtCnt = 0
                    tmpLine = line.strip('{} \t\n\r')
                    segmentInsertOrder[tmpLine.split()[1]] = insertCnt
                    tmpHocLabelList.append(tmpLine.split()[1])
                    insertCnt += 1
                if ('dend' in line or 'BasalDendrite' in line) and 'create' in line:
                    tmpLabelList.append('Dendrite')
                    readPts = 1
                    edgePtCnt = 0
                    tmpLine = line.strip('{} \t\n\r')
                    segmentInsertOrder[tmpLine.split()[1]] = insertCnt
                    tmpHocLabelList.append(tmpLine.split()[1])
                    insertCnt += 1
                if 'apical' in line and 'create' in line:
                    tmpLabelList.append('ApicalDendrite')
                    readPts = 1
                    edgePtCnt = 0
                    tmpLine = line.strip('{} \t\n\r')
                    segmentInsertOrder[tmpLine.split()[1]] = insertCnt
                    tmpHocLabelList.append(tmpLine.split()[1])
                    insertCnt += 1
                if 'axon' in line and 'create' in line:
                    tmpLabelList.append('Axon')
                    readPts = 1
                    edgePtCnt = 0
                    tmpLine = line.strip('{} \t\n\r')
                    segmentInsertOrder[tmpLine.split()[1]] = insertCnt
                    tmpHocLabelList.append(tmpLine.split()[1])
                    insertCnt += 1
                
                '''determine connectivity'''
                if 'connect' in line:
#                        if 'soma' in line:
#                            segmentParentMap[insertCnt-1] = 'soma'
#                            continue
                    splitLine = line.split(',')
                    parentStr = splitLine[1].strip()
                    name_end = parentStr.find('(')
                    conEnd = parentStr.find(')')
                    segmentParentMap[insertCnt - 1] = parentStr[:name_end]
                    segmentConMap[insertCnt - 1] = float(parentStr[name_end + 1:conEnd])
                    
#            end for loop
        
        '''make sure EOF doesn't mess anything up'''
        if len(tmpEdgePtCntList) == len(tmpLabelList) - 1 and edgePtCnt:
            tmpEdgePtCntList.append(edgePtCnt)
        
        '''put everything into Cell'''
        ptListIndex = 0
        if len(tmpEdgePtCntList) == len(tmpLabelList):
            for n in range(len(tmpEdgePtCntList)):
#                data belonging to this segment
                thisSegmentID = tmpLabelList[n]
                thisNrOfEdgePts = tmpEdgePtCntList[n]
                thisSegmentPtList = tmpEdgePtList[ptListIndex:ptListIndex + thisNrOfEdgePts]
                thisSegmentDiamList = tmpDiamList[ptListIndex:ptListIndex + thisNrOfEdgePts]
                ptListIndex += thisNrOfEdgePts
#                create edge
                segment = Edge()
                segment.label = thisSegmentID
                segment.hocLabel = tmpHocLabelList[n]
                segment.edgePts = thisSegmentPtList
                segment.diameterList = thisSegmentDiamList
                if thisSegmentID != 'Soma':
                    segment.parentID = segmentInsertOrder[segmentParentMap[n]]
                    segment.parentConnect = segmentConMap[n]
                else:
                    segment.parentID = None
                if segment.is_valid():
                    cell.append(segment)
                else:
                    raise IOError('Logical error reading hoc file: invalid segment')
            
        else:
            raise IOError('Logical error reading hoc file: Number of labels does not equal number of edges')
        
        return cell
    
def read_scalar_field(fname=''):
    if not fname.endswith('.am') and not fname.endswith('.AM'):
        raise IOError('Input file is not an Amira Mesh file!')
    
    with mdbopen(fname, 'r') as meshFile:
#            log.info "Reading Amira Mesh file", fname
        mesh = None
        extent, dims, bounds, origin, spacing = [], [], [], [], [0.,0.,0.]
        dataSection, hasExtent, hasBounds = False, False, False
        index = 0
        for line in meshFile:
            if line.strip():
#                    set up lattice
                if not dataSection:
                    if 'define' in line and 'Lattice' in line:
                        dimStr = line.strip().split()[-3:]
                        for dim in dimStr:
                            dims.append(int(dim))
                        for dim in dims:
                            extent.append(0)
                            extent.append(dim-1)
                        hasExtent = True
                    if 'BoundingBox' in line:
                        bBoxStr = line.strip(' \t\n,').split()[-6:]
                        for val in bBoxStr:
                            bounds.append(float(val))
                        for i in range(3):
                            origin.append(bounds[2*i])
                        hasBounds = True
                    if hasExtent and hasBounds and mesh is None:
                        for i in range(3):
                            spacing[i] = (bounds[2*i+1]-bounds[2*i])/(extent[2*i+1]-extent[2*i])
                            bounds[2*i+1] += 0.5*spacing[i]
                            bounds[2*i] -= 0.5*spacing[i]
                            origin[i] -= 0.5*spacing[i]
                        mesh = np.empty(shape=dims)
                    if '@1' in line and line[:2] == '@1':
                        dataSection = True
                        continue
#                    main data loop
                else:
                    data = float(line.strip())
                    k = index//(dims[0]*dims[1])
                    j = index//dims[0] - dims[1]*k
                    i = index - dims[0]*(j + dims[1]*k)
                    mesh[i,j,k] = data
                    index += 1
#                        log.info 'i,j,k = %s,%s,%s' % (i, j, k)
        
        return scalar_field.ScalarField(mesh, origin, extent, spacing, bounds)

def read_synapse_realization(fname):
    if not fname.endswith('.syn') and not fname.endswith('.SYN'):
        raise IOError('Input file is not a synapse realization file!')
    
    synapses = {}
    with mdbopen(fname, 'r') as synFile:
        for line in synFile:
            stripLine = line.strip()
            if not stripLine or stripLine[0] == '#':
                continue
            splitLine = stripLine.split('\t')
            synType = splitLine[0]
            sectionID = int(splitLine[1])
            sectionx = float(splitLine[2])
            if synType not in synapses:
                synapses[synType] = [(sectionID, sectionx)]
            else:
                synapses[synType].append((sectionID, sectionx))
    
    return synapses

def read_pruned_synapse_realization(fname):
    if not fname.endswith('.syn') and not fname.endswith('.SYN'):
        raise IOError('Input file is not a synapse realization file!')
    
    synapses = {}
    with mdbopen(fname, 'r') as synFile:
        for line in synFile:
            stripLine = line.strip()
            if not stripLine or stripLine[0] == '#':
                continue
            splitLine = stripLine.split('\t')
            synType = splitLine[0]
            sectionID = int(splitLine[1])
            sectionx = float(splitLine[2])
            pruned = int(splitLine[3])
            if synType not in synapses:
                synapses[synType] = [(sectionID, sectionx, pruned)]
            else:
                synapses[synType].append((sectionID, sectionx, pruned))
    
    return synapses

def read_functional_realization_map(fname):
    '''
    reads list of all functional connections
    coded by tuples (cell type, presynaptic cell index, synapse index).
    Only valid for anatomical synapse realization given by anatomicalID
    '''
    if not fname.endswith('.con') and not fname.endswith('.CON'):
        raise IOError('Input file is not a functional map realization file!')
    
    connections = {}
    anatomicalID = None
    lineCnt = 0
    with mdbopen(fname, 'r') as synFile:
        for line in synFile:
            stripLine = line.strip()
            if not stripLine:
                continue
            lineCnt += 1
            if stripLine[0] == '#':
                if lineCnt == 2:
                    splitLine = stripLine.split(' ')
                    anatomicalID = splitLine[-1]
                continue
            splitLine = stripLine.split('\t')
            cellType = splitLine[0]
            cellID = int(splitLine[1])
            synID = int(splitLine[2])
            if cellType not in connections:
                connections[cellType] = [(cellType, cellID, synID)]
            else:
                connections[cellType].append((cellType, cellID, synID))
    return connections, anatomicalID

def read_synapse_activation_file(fname):
    '''
    reads list of all functional synapses and their activation times.
    Input: file of format:
        synapse type\\tsynapse ID\\tsoma distance\\tsection ID\\tsection pt ID\\tdendrite label\\tactivation times
    returns: dictionary with cell types as keys and list of synapse locations and activation times,
    coded as tuples: (synapse ID, section ID, section pt ID, [t1, t2, ... , tn])
    '''
#    log.info 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
#    log.info 'reading synapse activation file'
#    log.info 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    synapses = {}
    lineCnt = 0
    with mdbopen(fname, 'r') as synFile:
        for line in synFile:
            if not lineCnt:
                lineCnt += 1
                continue
            stripLine = line.strip()
            if not stripLine:
                continue
            splitLine = stripLine.split('\t')
            #===================================================================
            # clunky support for analysis of old format synapse activation files...
            #===================================================================
            old = False
            if len(splitLine) == 6:
                old = True
            if old:
                cellType = splitLine[0]
                synID = -1
                somaDist = float(splitLine[1])
                secID = int(splitLine[2])
                ptID = int(splitLine[3])
            if not old:
                cellType = splitLine[0]
                synID = int(splitLine[1])
                somaDist = float(splitLine[2])
                secID = int(splitLine[3])
                ptID = int(splitLine[4])
            synTimes = []
            synTimesStr = splitLine[-1].split(',')
            for tStr in synTimesStr:
                if tStr:
                    synTimes.append(float(tStr))
            if cellType not in synapses:
                synapses[cellType] = [(synID, secID, ptID, synTimes, somaDist)]
            else:
                synapses[cellType].append((synID, secID, ptID, synTimes, somaDist))
            lineCnt += 1
    return synapses

def read_complete_synapse_activation_file(fname):
    '''
    reads list of all functional synapses and their activation times.
    Input: file of format:
        synapse type\\tsynapse ID\\tsoma distance\\tsection ID\\tsection pt ID\\tdendrite label\\tactivation times
    returns: dictionary with cell types as keys and list of synapse locations and activation times,
    coded as tuples: (synapse ID, soma distance, section ID, point ID, structure label, [t1, t2, ... , tn])
    '''
    synapses = {}
    with mdbopen(fname, 'r') as synFile:
        for line in synFile:
            line = line.strip()
            if not line:
                continue
            if line[0] == '#':
                continue
            splitLine = line.split('\t')
            cellType = splitLine[0]
            synID = int(splitLine[1])
            somaDist = float(splitLine[2])
            secID = int(splitLine[3])
            ptID = int(splitLine[4])
            structure = splitLine[5]
            synTimes = []
            synTimesStr = splitLine[6].split(',')
            for tStr in synTimesStr:
                if tStr:
                    synTimes.append(float(tStr))
            if cellType not in synapses:
                synapses[cellType] = [(synID, somaDist, secID, ptID, structure, synTimes)]
            else:
                synapses[cellType].append((synID, somaDist, secID, ptID, structure, synTimes))
    
    return synapses

def read_spike_times_file(fname):
    '''
    reads list of all trials and spike times within these trials.
    Input: file of format:
        trial nr.\\tactivation times (comma-separated list or empty)
    returns:
        dictionary with trial numbers as keys (integers), and tuples of spike times
        in each trial as values
    '''
    spikeTimes = {}
    with mdbopen(fname, 'r') as spikeTimeFile:
        for line in spikeTimeFile:
            line = line.strip()
            if not line:
                continue
            if line[0] == '#':
                continue
            splitLine = line.split('\t')
            trial = int(splitLine[0])
            tmpTimes = []
            if len(splitLine) > 1:
                spikeTimesStr = splitLine[1].split(',')
                for tStr in spikeTimesStr:
                    if tStr:
                        tmpTimes.append(float(tStr))
            if trial not in spikeTimes:
                spikeTimes[trial] = tuple(tmpTimes)
            else:
                errstr = 'Error reading spike times file: duplicate trial number (trial %d)' % trial
                raise RuntimeError(errstr)
    
    return spikeTimes

def read_synapse_weight_file(fname):
    '''
    reads list of all anatomical synapses and their maximum conductance values.
    Input: file of format:
        synapse type\\\tsynapse ID\tsection ID\\tsection pt ID\\treceptor type (string)\\tconductance values
    Returns: two (!!!) dictionaries with cell types as keys, ordered the same as the anatomical synapses:
        1st with section ID and pt ID, 2nd with synaptic weights, coded as dictionaries
        (keys=receptor strings) containing weights: (gmax_0, gmax_1, ... , gmax_n)
    '''
#    log.info 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
#    log.info 'reading synapse strength file'
#    log.info 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    synWeights, synLocations = {}, {}
    lineCnt = 0
    with mdbopen(fname, 'r') as synFile:
        for line in synFile:
            if not lineCnt:
                lineCnt += 1
                continue
            stripLine = line.strip()
            if not stripLine:
                continue
            splitLine = stripLine.split('\t')
            cellType = splitLine[0]
            synID = int(splitLine[1])
            secID = int(splitLine[2])
            ptID = int(splitLine[3])
            receptorType = splitLine[4]
            synWeightList = []
            synWeightsStr = splitLine[5].split(',')
            for gStr in synWeightsStr:
                if gStr:
                    synWeightList.append(float(gStr))
            if cellType not in synLocations:
                synLocations[cellType] = {}
            synLocations[cellType][synID] = (secID, ptID)
            if cellType not in synWeights:
                synWeights[cellType] = []
            if len(synWeights[cellType]) < synID + 1:
                synWeights[cellType].append({})
            synWeights[cellType][synID][receptorType] = synWeightList
            lineCnt += 1
    return synWeights, synLocations

def read_landmark_file(landmarkFilename):
    '''
    returns list of (x,y,z) points
    '''
    if not landmarkFilename.endswith('.landmarkAscii'):
        errstr = 'Wrong input format: has to be landmarkAscii format'
        raise RuntimeError(errstr)
    
    landmarks = []
    with mdbopen(landmarkFilename, 'r') as landmarkFile:
        readPoints = False
        for line in landmarkFile:
            stripLine = line.strip()
            if not stripLine:
                continue
            if stripLine[:2] == '@1':
                readPoints = True
                continue
            if readPoints:
                splitLine = stripLine.split()
                x = float(splitLine[0])
                y = float(splitLine[1])
                z = float(splitLine[2])
                landmarks.append((x,y,z))
    
    return landmarks

if __name__ == '__main__':
#    testHocFname = raw_input('Enter hoc filename: ')
#    testReader = Reader(testHocFname)
#    testReader.read_hoc_file()
#    testAmFname = raw_input('Enter Amira filename: ')
    for i in range(1000):
        testAmFname = 'SynapseCount.14678.am'
        read_scalar_field(testAmFname)
    log.info('Done!')
