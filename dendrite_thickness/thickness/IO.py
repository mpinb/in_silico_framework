"""
IO Module

==========
This module contains methods to read and write data with different formats.


File extensions
----------------------

1. .am
Capabilities:
- Reading  all data point with their associated attribute (e.g. VertexLabels, thickness)
- Writing data am_points in 3d and their corresponding thickness
Limitations:
- Not able to read other data than 3d positional am_points and their thickness
- Only able to read and write in ascii format (In this module in the class amira_utils the are methods one can use to
 convert amira binary format to ascii format, for more details look at the amira_utils class docstring)

2 .hoc
Capabilities:
- Reading data am_points (point coordinates and their associated thickness) of kind:
    1. ApicalDendrite
    2. BasalDendrite
    3. Dendrite
    4. Soma
from the hoc file.
- Writing data am_points (as kind of what it can read) in 3d and their associated thickness
Limitations:
- Not able to construct the tree structure from the hoc file.
- Not able to read the white matter data.

3 .hx
Capabilities:
- Read transformation matrix (the one for complete morphology not
each transformation for each file.) and the path files of the each slice.
Limitations:
- To read the transformations of each slice, it needs to connect to Amira.

"""
import re
import os
from random import randrange
import numpy as np


class Am:

    def __init__(self, input_path, output_path=None, read_ = True):

        if output_path is None:
            output_path = os.path.dirname(input_path) + "output_" + str(randrange(100))

        self.commands = {}
        self.config = {}
        self.input_path = input_path
        self.output_path = output_path
        self.transformation_matrix_exist = False
        self.transformation_matrix = np.array([[ 1.,  0.,  0.,  0.],
                                                [ 0.,  1.,  0.,  0.],
                                                [ 0.,  0.,  1.,  0.],
                                                [ 0.,  0.,  0.,  1.]])
        self.all_data = {}
        if read_:
            self.read()

    def read(self):
        """
        Reading all data of of the am file

        """
        self._read_config_and_commands()
        config_end = self.config_end
        with open(self.input_path, 'r') as f:
            lines = f.readlines()
            for cs in self.commands:
                command_sign = self.commands[cs]
                # command_sign (eg. @1 or @2 ) are the initialized value of commands dict keys
                # which provided by the _read_commands function.
                data_section = False
                data = []
                for line in lines[config_end:]:
                    line = line.replace('\r\n', '\n')
                    if line.rfind(command_sign) > -1:
                        data_section = True
                        continue
                    elif data_section and (line == '\n' or '@' in line):
                        data_section = False
                    elif data_section and line != '\n':
                        d = list(map(float, line.strip().split(' ')))
                        # d = read_numbers_in_line(line)
                        data.append(d)

                self.all_data[cs] = data

    def _read_transformation_matrix(self):
        """
        This method can extract the amira transformation matrix written in am file.

        """
        input_path = self.input_path

        matrix = []
        vector = []
        row = []
        with open(input_path, 'r') as f:
            lines = f.readlines()
            for idx, line in enumerate(lines):
                if line.rfind("TransformationMatrix") > -1:
                    # vector = read_numbers_in_line(line)
                    line = line.strip()
                    line = line.strip('TransformationMatrix')
                    line = line.split(' ')
                    vector = [float(l.strip()) for l in line if l]
            for i in range(4):
                for j in range(4):
                    k = j + i * 4
                    row.append(vector[k])
                matrix.append(row)
                row = []
        self.transformation_matrix = np.array(matrix).T

    def write(self):
        """
        Writing data from a dictionary into an am file.
        """
        self._write_from_dict()

    def _write_from_dict(self):
        def format_number(x):
            if x == int(x):
                return str(int(x))
            else:
                return  '{:.15e}'.format(x)


        with open(self.output_path, "w") as data_file:
            data_file.writelines(self.all_data["config"])
            for cs in self._commands_order:
                data_file.write("\n")
                data_file.write(cs + ' ' + self.commands[cs])
            data_file.write("\n\n")
            data_file.write("# Data section follows")
            data_file.write("\n")

            for cs in self._commands_order:
                data_file.write("\n")
                data_file.write(self.commands[cs])
                data_file.write("\n")
                for data in self.all_data[cs]:
                    
                    string = ' '.join(map(format_number, data))
                    for item in string:
                        data_file.write(item)
                    data_file.write("\n")

    def _read_config_and_commands(self):
        with open(self.input_path, 'r') as fc:
            lines = fc.readlines()
            commands = {}
            commands_order = []
            header_end = None
            for idx, line in enumerate(lines):
                if line.rfind("TransformationMatrix") > -1:
                    self.transformation_matrix_exist = True
                    self._read_transformation_matrix()
                if line.rfind("@") > -1:
                    if header_end is None:
                        header_end = idx
                    # command_sign supposes to hold the values like @1 or @2 or ...
                    command_sign = "@" + line[line.rfind("@") + 1:].strip()
                    if line.replace(command_sign, "").strip() != "":
                        c = line.replace(command_sign, "").strip()
                        commands_order.append(c)
                        commands[c] = command_sign
                    else: # searches for the first isolated occurence of @[number], which indicates beginning of data section
                        config_end = idx
                        break
            self.all_data["config"] = lines[:header_end]
        self.commands = commands
        self.config_end = config_end
        self._commands_order = commands_order

    def add_data(self, cs, data):
        max_command = max([int(v.strip('@ ')) for v in list(self.commands.values())])
        self.commands[cs] = '@' + str(max_command + 1)
        self.all_data[cs] = data
        self._commands_order.append(cs)


class Hoc:

    def __init__(self, input_path, output_path=None):

        if output_path is None:
            output_path = os.path.dirname(input_path) + "output_" + str(randrange(100))
        self.output_path = output_path
        self.input_path = input_path
        self.edges = read_hoc_file(input_path)
        self.all_data = {"thicknesses": [], "nodes": [], "am_points": []}
        self._process()

    def _process(self):
        self._extract_nodes()
        self._extract_all_pts()

    def _extract_nodes(self):
        nodes = []
        for e in self.edges:
            nodes.append(e.edgePts[0])
            nodes.append(e.edgePts[-1])
        self.all_data['nodes'] = nodes

    def _extract_all_pts(self):
        pts = []
        for e in self.edges:
            pts.extend(e.edgePts)
        self.all_data['am_points'] = pts

    def update_thicknesses(self):
        """
        # Writing thicknesses of am_points to a specific hoc file.
        # basically it do this: reading a file without the
        # thicknesses of neuronal am_points and add the thickness to them in another hoc file
        
        Inputs:
        - 1. thicknesses: A list of thicknesses, which are floats values, the order of
        thicknesses list must be match with the oder of self.profile_data["am_points"]
        
        - 2. input_path, if not given it will use self.input_path, the method will use this 
        as a sample hoc file to create another Hoc file with thicknesses added to the corresponding am_points
        
        - 3. output_path: The path of the desired output hoc file. If not given, the method will use self.output_path.   
        - 3. output_path: The path of the desired output hoc file. If not given, the method will use self.output_path.
        """
        thicknesses = self.all_data["thicknesses"]
        hoc_points = self.all_data["am_points"]
        input_path = self.input_path
        output_path = self.output_path

        with open(input_path, 'r') as readHocFile:
            with open(output_path, 'w') as writeHocFile:
                lines = readHocFile.readlines()
                neuron_section = False

                in_neuron_line_number = 0

                for lineNumber, line in enumerate(lines):
                    soma = line.rfind("soma")
                    dend = line.rfind("dend")
                    apical = line.rfind("apical")
                    createCommand = line.rfind("create")
                    pt3daddCommand = line.rfind("pt3dadd")

                    if not neuron_section and ((createCommand > -1)
                                               and (soma + apical + dend > -3)):
                        neuron_section = True

                    if neuron_section and (line == '\n'):
                        neuron_section = False

                    if (pt3daddCommand > -1) and neuron_section:

                        thickness = thicknesses[in_neuron_line_number]
                        hoc_point = hoc_points[in_neuron_line_number]
                        line = line.replace("pt3dadd", "")
                        matches = re.findall(r'-?\d+\.\d?\d+|\-?\d+', line)
                        point = list(map(float, matches))

                        writeHocFile.write('{{pt3dadd({:f},{:f},{:f},{:f})}}\n'.format(hoc_point[0],
                                                                                       hoc_point[1],
                                                                                       hoc_point[2],
                                                                                       thickness))
                        in_neuron_line_number = in_neuron_line_number + 1
                    else:
                        writeHocFile.write(line)


class Amira_utils:

    def __init__(self):
        pass


def read_numbers_in_line(line):
    """
    Find numbers of in a line, the matches is a list contains
    the numbers that the regex command matches in the line.
    The number formats that this regex support are as an examples:
    egs:
    - 12 -> 12.0
    - -12 -> -12.0
    - 1.22 -> 1.22
    - -1.22 -> -1.22
    - 2.407640075683594e+02  -> 2.407640075683594e+02
    - -2.407640075683594e+02 -> -2.407640075683594e+02
    - -2.407640075683594e-02 -> -2.407640075683594e-02
    - 2.407640075683594e-02 -> 2.407640075683594e-02
    - -2.407640075683594 -> -2.407640075683594
    - 2.521719970703125e+02, 3.437120056152344e+02, 6.554999947547913e-01, -> 2.521719970703125e+02
    3.437120056152344e+02 6.554999947547913e-01

    """
    matches = re.findall(r'-?\d+\.\d+[e]?[+-]?\d+|\-?\d+[e]?', line)
    if not matches:
        raise RuntimeError(
            "Expected number in line {} but did not set_transformation_matrix_by_aligned_points any".format(line))
    data = list(map(float, matches))
    return data


class Edge(object):
    '''
    Edge obj contains list of am_points,
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


def read_landmark_file(landmarkFilename):
    '''
    returns list of (x,y,z) am_points
    '''
    if not landmarkFilename.endswith('.landmarkAscii'):
        errstr = 'Wrong input format: has to be landmarkAscii format'
        raise RuntimeError(errstr)

    landmarks = []
    with open(landmarkFilename, 'r') as landmarkFile:
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
                landmarks.append((x, y, z))

    return landmarks
