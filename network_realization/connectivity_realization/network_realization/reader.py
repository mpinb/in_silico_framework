
'''
Created on Mar 8, 2012

@author: regger
'''

import numpy as np

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
#    TODO: skip reading axonal sections! Only interested in dendrites/soma here
    if not fname.endswith('.hoc') and not fname.endswith('.HOC'):
        raise IOError('Input file is not a .hoc file!')
    
    with open(fname, 'r') as neuronFile:
        print("Reading hoc file", fname)
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
                    readPts = 0
#                    tmpLabelList.append('Axon')
#                    readPts = 1
#                    edgePtCnt = 0
#                    tmpLine = line.strip('{} \t\n\r')
#                    segmentInsertOrder[tmpLine.split()[1]] = insertCnt
#                    tmpHocLabelList.append(tmpLine.split()[1])
#                    insertCnt += 1
                
                '''determine connectivity'''
                if 'connect' in line and readPts:
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
    

