
import os
import re
import math

# Reading all neuronal points of a hoc file
def hocFileComplete(inputFilePath):
    with open(inputFilePath, 'r') as hocFile:
        lines = hocFile.readlines()
        neuron_section = False
        points = []

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
                line = line.replace("pt3dadd", "")
                matches = re.findall('-?\d+\.\d?\d+|\-?\d+', line)
                point = map(float, matches)
                points.append(point)
    return points


# Reading hoc file with only two points (top and bottom) from each section of
# neuronal points of a hoc file
def hocFileReduced(inputFilePath):
    with open(inputFilePath, 'r') as hocFile:
        lines = hocFile.readlines()
        neuron_section = False
        points = []
        lastPoint = []

        in_neuron_line_number = 0

        for lineNumber, line in enumerate(lines):
            # raw_input("Press Enter to continue...")
            soma = line.rfind("soma")
            dend = line.rfind("dend")
            apical = line.rfind("apical")
            createCommand = line.rfind("create")
            pt3daddCommand = line.rfind("pt3dadd")
            # print("line:")
            # print(lineNumber)
            # print("the content:")
            # print(line)
            if not neuron_section and ((createCommand > -1)
                                       and (soma + apical + dend > -3)):
                neuron_section = True
                # print("in_neuron True")

            if neuron_section and (line == '\n'):
                neuron_section = False
                in_neuron_line_number = 0
                points.append(lastPoint)
                lastPoint = []
                # print("in_neuron True and line empty")

            if (pt3daddCommand > -1) and neuron_section:
                in_neuron_line_number = in_neuron_line_number + 1;
                line = line.replace("pt3dadd", "")
                matches = re.findall('-?\d+\.\d?\d+|\-?\d+', line)
                point = map(float, matches)
                # print("in p3dadd command")
                if (in_neuron_line_number == 1):
                    points.append(point)
                else:
                    lastPoint = point
    return points


# Reading all points of am file with also their radius form the
# thickness part of the file
def amFile(inputFilePath):
    with open(inputFilePath, 'r') as amFile:
        lines = amFile.readlines()
        points = []
        rads = []
        pointsWithRad = []
        in_edge_section = False
        in_thickness_section = False

        for lineNumber, line in enumerate(lines):

            edge_sign = line.rfind("@8")
            EdgePointCoordinates = line.rfind("EdgePointCoordinates")

            thickness_sign = line.rfind("@9")
            thickness = line.rfind("thickness")

            if edge_sign > -1 and EdgePointCoordinates < 0:
                in_edge_section = True
                continue

            if thickness_sign > -1 and thickness < 0:
                in_thickness_section = True
                continue

            if in_edge_section and (line != '\n'):
                matches = re.findall('-?\d+\.\d+e[+-]?\d+', line)
                point = map(float, matches)
                points.append(point)

            if in_edge_section and (line == '\n'):
                in_edge_section = False

            if in_thickness_section and (line != '\n'):
                matches = re.findall('-?\d+\.\d+e[+-]?\d+', line)
                if matches == []:
                    matches = [0.0,0.0]
                rad = map(float, matches)
                rads.append(rad)

            if in_thickness_section and (line == '\n'):
                in_thickness_section = False

        for idx, point in enumerate(points):
            pointsWithRad.append([point[0], point[1], point[2], rads[idx][0]])

    return pointsWithRad


# Input a folder path which contains the am files
# Output the am files with radius as a dictionary of am files paths
# and a full array of all points with their radii

def multipleAmFiles(inputFolderPath):
    oneAmFilePoints =[]
    allAmPoints = []
    amFilesSet = {}

    for am_file in os.listdir(inputFolderPath):
        oneAmFilePoints =[]
        if am_file.endswith(".am"):
            pathToAmFile = inputFolderPath + str(am_file)
            oneAmFilePoints = amFile(pathToAmFile)
            amFilesSet[str(am_file)] = oneAmFilePoints
            allAmPoints = allAmPoints + oneAmFilePoints
    return allAmPoints, amFilesSet
