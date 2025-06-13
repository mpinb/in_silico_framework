# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.

import os
import re
import math


def convert_point(p, x_res=0.092, y_res=0.092, z_res=1.0):
    out = []
    scaling = [x_res, y_res, z_res]
    for lv, pp in enumerate(p):
        try:
            s = scaling[lv]
        except IndexError:
            s = 1
        out.append(pp * s)
    return out


def hocFileComplete(inputFilePath):
    '''Reading all neuronal points of a hoc file'''
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

            if not neuron_section and ((createCommand > -1) and
                                       (soma + apical + dend > -3)):
                neuron_section = True

            if neuron_section and (line == '\n'):
                neuron_section = False

            if (pt3daddCommand > -1) and neuron_section:
                line = line.replace("pt3dadd", "")
                matches = re.findall('-?\d+\.\d?\d+|\-?\d+', line)
                point = list(map(float, matches))
                points.append(point)
    return points


def hocFileReduced(inputFilePath):
    """
    Reading hoc file with only two points (top and bottom) from each section of
    neuronal points of a hoc file

    """
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
            if not neuron_section and ((createCommand > -1) and
                                       (soma + apical + dend > -3)):
                neuron_section = True
                # print("in_neuron True")

            if neuron_section and (line == '\n'):
                neuron_section = False
                in_neuron_line_number = 0
                points.append(lastPoint)
                lastPoint = []
                # print("in_neuron True and line empty")

            if (pt3daddCommand > -1) and neuron_section:
                in_neuron_line_number = in_neuron_line_number + 1
                line = line.replace("pt3dadd", "")
                matches = re.findall('-?\d+\.\d?\d+|\-?\d+', line)
                point = list(map(float, matches))
                # print("in p3dadd command")
                if (in_neuron_line_number == 1):
                    points.append(point)
                else:
                    lastPoint = point
    return points


def amFile(inputFilePath):
    """
    Reading all points of am file with also their radius form the
    thickness part of the file

    """
    with open(inputFilePath, 'r') as amFile:
        lines = amFile.readlines()
        points = []
        rads = []
        pointsWithRad = []
        in_edge_section = False
        in_thickness_section = False

        for l_number, l in enumerate(lines):
            line_thickness = l.rfind("float thickness")
            line_edge = l.rfind("float[3] EdgePointCoordinates")
            char_idx = 0
            if line_thickness > -1:
                char_idx = l.rfind("@")
                thickness_sign_number = l[char_idx + 1]
                thickness_sign = "@" + thickness_sign_number

            elif (line_edge > -1):
                char_idx = l.rfind("@")
                edge_sign_number = l[char_idx + 1]
                edge_sign = "@" + edge_sign_number

        for lineNumber, line in enumerate(lines):

            edge_sign_presense = line.rfind(edge_sign)
            EdgePointCoordinates = line.rfind("EdgePointCoordinates")

            thickness_sign_presense = line.rfind(thickness_sign)
            thickness = line.rfind("thickness")

            if edge_sign_presense > -1 and EdgePointCoordinates < 0:
                in_edge_section = True
                continue

            if thickness_sign_presense > -1 and thickness < 0:
                in_thickness_section = True
                continue

            if in_edge_section and (line != '\n'):
                # please test if their results are compatible or not
                # matches = re.findall('-?\d+\.\d+e[+-]?\d+', line)
                matches = re.findall('-?\d+\.\d+[e]?[+-]?\d+', line)
                point = list(map(float, matches))
                points.append(point)

            if in_edge_section and (line == '\n'):
                in_edge_section = False

            if in_thickness_section and (line != '\n'):
                # please test if their results are compatible or not
                # matches = re.findall('-?\d+\.\d+e[+-]?\d+', line)
                matches = re.findall('-?\d+\.\d+[e]?[+-]?\d+', line)
                if matches == []:
                    matches = [0.0, 0.0]
                rad = list(map(float, matches))
                rads.append(rad)

            if in_thickness_section and (line == '\n'):
                in_thickness_section = False

        for idx, point in enumerate(points):
            pointsWithRad.append([point[0], point[1], point[2], rads[idx][0]])

    return pointsWithRad


def multipleAmFiles(inputFolderPath):
    """
    Input a folder path which contains the am files
    Output the am files with radius as a dictionary of am files paths
    and a full array of all points with their radii
    """

    oneAmFilePoints = []
    allAmPoints = []
    amFilesSet = {}

    for am_file in os.listdir(inputFolderPath):
        oneAmFilePoints = []
        if am_file.endswith(".am"):
            pathToAmFile = inputFolderPath + str(am_file)
            oneAmFilePoints = amFile(pathToAmFile)
            amFilesSet[str(am_file)] = oneAmFilePoints
            allAmPoints = allAmPoints + oneAmFilePoints
    return allAmPoints, amFilesSet
