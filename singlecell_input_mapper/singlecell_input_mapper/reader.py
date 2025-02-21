'''Read in hoc files, Amira Mesh files, and spreadsheets with connection probabilities.
'''

import numpy as np
from . import scalar_field
from data_base.dbopen import dbopen

__author__ = 'Robert Egger'
__date__ = '2012-03-08'

class _Edge(object):
    '''Convenience class around NEURON's section objects.

    The purpose of this class is for private use in reading in hoc files: it should not be invoked directly.

    See also:
        :py:mod:`single_cell_parser` also contains a :py:class:`~single_cell_parser.reader._Edge` class.

    Attributes:
        label (str): The type of the segment (e.g. 'Soma', 'Dendrite', 'ApicalDendrite')
        hocLabel (str): The label of the segment as defined in the hoc file.
        edgePts (list): A list of points that define the segment.
        diameterList (list): A list of diameters for each point in edgePts.
        parentID (int): The ID of the parent segment.
        parentConnect (float): The parent segment.
    '''

    def is_valid(self):
        """Check if this edge is valid.
        
        Edges are only valid if they have a :paramref:`label`, a :paramref:`hocLabel`, and at least one :paramref:`edgePts`.
        
        Returns:
            bool: True if the edge is valid, False otherwise.
        """
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
    """Reads a hoc file and returns a list of Edge objects.
    
    This list of sections is parsed to a :py:class:`~singlecell_input_mapper.singlecell_input_mapper.cell.CellParser` object
    using :py:meth:`singlecell_input_mapper.singlecell_input_mapper.cell.CellParser.spatialgraph_to_cell`.
    
    See also:
        The module :py:mod:`single_cell_parser` also conains a :py:meth:`~single_cell_parser.reader.read_hoc_file` 
        method. A notable difference is that this method does **not** read in axon sections.

    Args:
        fname (str): The name of the file to be read.

    Returns:
        list: A list of :py:class:`Edge` objects.
    """
    #    TODO: skip reading axonal sections! Only interested in dendrites/soma here
    if not fname.endswith('.hoc') and not fname.endswith('.HOC'):
        raise IOError('Input file is not a .hoc file!')

    with dbopen(fname, 'r') as neuronFile:
        print("Reading hoc file", fname)
        # cell = co.Cell()
        # simply store list of edges
        # cell is parsed in CellParser
        cell = []
        
        # set up all temporary data structures that hold 
        # the cell morphology before turning it into a Cell
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
                # 0. skip comments
                if '/*' in line and '*/' in line:
                    continue
                    # '''ignore daVinci registration'''
                    # if '/* EOF */' in line:
                    #     break
                
                # 1. read pts belonging to current segment
                if readPts:
                    if 'Spine' in line:
                        continue
                    if 'pt3dadd' in line:
                        ptStr = line.partition('(')[2].partition(')')[0]
                        ptStrList = ptStr.split(',')
                        tmpEdgePtList.append([
                            float(ptStrList[0]),
                            float(ptStrList[1]),
                            float(ptStrList[2])
                        ])
                        tmpDiamList.append(float(ptStrList[3]))
                        edgePtCnt += 1
                        continue
                    elif 'pt3dadd' not in line and edgePtCnt:
                        readPts = 0
                        tmpEdgePtCntList.append(edgePtCnt)
                        edgePtCnt = 0
                
                # 2. determine type of section and insert section name
                if 'soma' in line and 'create' in line:
                    tmpLabelList.append('Soma')
                    readPts = 1
                    edgePtCnt = 0
                    tmpLine = line.strip('{} \t\n\r')
                    segmentInsertOrder[tmpLine.split()[1]] = insertCnt
                    tmpHocLabelList.append(tmpLine.split()[1])
                    insertCnt += 1
                if ('dend' in line or
                        'BasalDendrite' in line) and 'create' in line:
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
                    # tmpLabelList.append('Axon')
                    # readPts = 1
                    # edgePtCnt = 0
                    # tmpLine = line.strip('{} \t\n\r')
                    # segmentInsertOrder[tmpLine.split()[1]] = insertCnt
                    # tmpHocLabelList.append(tmpLine.split()[1])
                    # insertCnt += 1
                
                # 3. determine connectivity
                if 'connect' in line and readPts:
                    # if 'soma' in line:
                    #   segmentParentMap[insertCnt-1] = 'soma'
                    #   continue
                    splitLine = line.split(',')
                    parentStr = splitLine[1].strip()
                    name_end = parentStr.find('(')
                    conEnd = parentStr.find(')')
                    segmentParentMap[insertCnt - 1] = parentStr[:name_end]
                    segmentConMap[insertCnt - 1] = float(parentStr[name_end +
                                                                   1:conEnd])
            # end for loop
        
        # 4. make sure EOF doesn't mess anything up
        if len(tmpEdgePtCntList) == len(tmpLabelList) - 1 and edgePtCnt:
            tmpEdgePtCntList.append(edgePtCnt)
        
        # 5. put everything into Cell
        ptListIndex = 0
        if len(tmpEdgePtCntList) == len(tmpLabelList):
            for n in range(len(tmpEdgePtCntList)):
                # data belonging to this segment
                thisSegmentID = tmpLabelList[n]
                thisNrOfEdgePts = tmpEdgePtCntList[n]
                thisSegmentPtList = tmpEdgePtList[ptListIndex:ptListIndex +
                                                  thisNrOfEdgePts]
                thisSegmentDiamList = tmpDiamList[ptListIndex:ptListIndex +
                                                  thisNrOfEdgePts]
                ptListIndex += thisNrOfEdgePts
                # create edge
                segment = _Edge()
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
                    raise IOError(
                        'Logical error reading hoc file: invalid segment')

        else:
            raise IOError(
                'Logical error reading hoc file: Number of labels does not equal number of edges'
            )

        return cell


def read_scalar_field(fname=''):
    """Read AMIRA scalar fields.
    
    Args:
        fname (str): The name of the file to be read.

    Raises:
        IOError: If the input file does not have a `.am` or `.AM` suffix.

    Returns:
        :py:class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`: A scalar field object.
    """
    if not fname.endswith('.am') and not fname.endswith('.AM'):
        raise IOError('Input file is not an Amira Mesh file!')

    with dbopen(fname, 'r') as meshFile:
        #            print "Reading Amira Mesh file", fname
        mesh = None
        extent, dims, bounds, origin, spacing = [], [], [], [], []
        dataSection, hasExtent, hasBounds, hasSpacing = False, False, False, False
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
                            extent.append(dim - 1)
                        hasExtent = True
                    if 'BoundingBox' in line:
                        bBoxStr = line.strip(' \t\n,').split()[-6:]
                        for val in bBoxStr:
                            bounds.append(float(val))
                        for i in range(3):
                            origin.append(bounds[2 * i])
                        hasBounds = True
                    if 'Spacing' in line:
                        spacingStr = line.strip(' \t\n,').split()[-3:]
                        for val in spacingStr:
                            spacing.append(float(val))
                        hasSpacing = True
                    if hasExtent and hasBounds and hasSpacing and mesh is None:
                        for i in range(3):
                            #spacing[i] = (bounds[2*i+1]-bounds[2*i])/(extent[2*i+1]-extent[2*i])
                            bounds[2 * i + 1] += 0.5 * spacing[i]
                            bounds[2 * i] -= 0.5 * spacing[i]
                            origin[i] -= 0.5 * spacing[i]
                        mesh = np.empty(shape=dims)
                    if '@1' in line and line[:2] == '@1':
                        dataSection = True
                        continue
                    # main data loop
                else:
                    data = float(line.strip())
                    k = index // (dims[0] * dims[1])
                    j = index // dims[0] - dims[1] * k
                    i = index - dims[0] * (j + dims[1] * k)
                    mesh[i, j, k] = data
                    index += 1


                        # print 'i,j,k = %s,%s,%s' % (i, j, k)

        return scalar_field.ScalarField(mesh, origin, extent, spacing, bounds)


def read_connections_spreadsheet(fname):
    """Reads a spreadsheet with connection probabilities between cell types

    Args:
        fname (str): The name of the file to be read
    
    Returns:
        dict: A dictionary with the following structure: {EXC: {celltype: {norm: value, ...}, ...}, INH: {...}}
        
    Example:
        
        >>> connectionsSpreadsheet = read_connections_spreadsheet('connections.csv')
        >>> connectionsSpreadsheet
        {'EXC': {
            celltype_1: {
                'SOMA_LENGTH': 0.1, 'SOMA_AREA': 0.2, ...
                },
            celltype_2: {...},
            },
        'INH': {...}
        }    
    """
    connectionSpreadsheet = {}
    connectionSpreadsheet['EXC'] = {}
    connectionSpreadsheet['INH'] = {}
    targetStructures = ('SOMA_LENGTH', 'APICAL_LENGTH', 'BASAL_LENGTH',
                        'SOMA_AREA', 'APICAL_AREA', 'BASAL_AREA')

    with dbopen(fname, 'r') as spreadsheet:
        for line in spreadsheet:
            stripLine = line.strip()
            if not stripLine:
                continue
            splitLine = stripLine.split('\t')
            if splitLine[0] == 'PRESYNAPTIC_CELLTYPE':
                continue
            else:
                preCellTypeStr = None
                if 'EXCITATORY' in splitLine[0]:
                    preCellTypeStr = 'EXC'
                if 'INHIBITORY' in splitLine[0]:
                    preCellTypeStr = 'INH'
                postCellType = splitLine[1]
                connectionSpreadsheet[preCellTypeStr][postCellType] = {}
                for i in range(len(targetStructures)):
                    connectionSpreadsheet[preCellTypeStr][postCellType][
                        targetStructures[i]] = float(splitLine[i + 2])

    return connectionSpreadsheet


def read_celltype_numbers_spreadsheet(fname):
    """Reads a spreadsheet with cell type numbers for each anatomical area.

    Args:
        fname (str): The name of the file to be read

    Returns:
        dict: A dictionary with the following structure: {anatomical_area: {cell_type: number_of_cells, ...}, ...}
    """
    columns = None
    cellTypeNumbers = {}

    with dbopen(fname, 'r') as spreadsheet:
        header = False
        for line in spreadsheet:
            stripLine = line.strip()
            if not stripLine:
                continue
            splitLine = stripLine.split('\t')
            if splitLine[0] == 'CELL TYPE':
                header = True
            if header:
                columns = [splitLine[i] for i in range(1, len(splitLine))]
                for col in columns:
                    cellTypeNumbers[col] = {}
                header = False
            else:
                cellType = splitLine[0]
                for i in range(len(columns)):
                    col = columns[i]
                    nrCells = int(splitLine[i + 1])
                    cellTypeNumbers[col][cellType] = nrCells

    return cellTypeNumbers


if __name__ == '__main__':
    #    testHocFname = raw_input('Enter hoc filename: ')
    #    testReader = Reader(testHocFname)
    #    testReader.read_hoc_file()
    #    testAmFname = raw_input('Enter Amira filename: ')
    #    for i in range(1000):
    #        testAmFname = 'SynapseCount.14678.am'
    #        read_scalar_field(testAmFname)
    #    print 'Done!'
    from six.moves import input
    testFname = input('Enter filename: ')
    #    spreadsheet = read_celltype_numbers_spreadsheet(testFname)
    spreadsheet = read_connections_spreadsheet(testFname)
