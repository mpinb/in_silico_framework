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

import numpy as np
import math
from scipy.spatial import ConvexHull


def constructEdges(points):
    """
    we give this function a set of points and it will reaturn us all edges,
    that is possible to create from those points;

    """

    class Edge:

        def __init__(self, distance, start, end):
            self.distance = distance
            self.start = start
            self.end = end

        def __str__(self):
            return str(self.__class__) + ": " + str(self.__dict__)

        def __repr__(self):
            return str(self.__class__) + ": " + str(self.__dict__)

    nodes = points

    distances = []
    edges = []
    i = 0
    j = 0
    for node_i in nodes:
        for node_j in nodes:
            tempDistance = distance(node_i, node_j)
            if (tempDistance not in distances):
                distances.append(tempDistance)
                tempEdge = Edge(tempDistance, node_i, node_j)
                edges.append(tempEdge)
            j = j + 1
        i = i + 1
        j = 0
    return edges


def findHullPoints(points):
    '''Find convex hull points from a set 3d points '''
    conPoints = []
    convexSet = ConvexHull(points)

    for verIndex in convexSet.vertices:
        conPoints.append(points[verIndex])
    return conPoints


def distance(point_i, point_j):
    """
    Calculate the distance of two points, specially for calculating
    the length of an edge
    """

    dist = math.sqrt((point_j[0] - point_i[0])**2 +
                     (point_j[1] - point_i[1])**2 +
                     (point_j[2] - point_i[2])**2)
    return dist


def longestOptimalEdges(edges, spanFactor):
    """
    here we sort the edges from the set of edges based on their length,
    we do not consider some edges, like the one that
    # their start or end points are so close to another start of edge or end points
    """
    sortedEdges = sorted(edges, key=lambda x: x.distance, reverse=True)
    sortedEdges_revers = sorted(edges, key=lambda x: x.distance, reverse=False)

    firstLongestEdge = sortedEdges[0]

    span = getMean(sortedEdges) / spanFactor
    shortestEdges = []

    for edg in sortedEdges_revers:
        shortEdge = edg
        side1 = distance(shortEdge.start, firstLongestEdge.start)
        side2 = distance(shortEdge.end, firstLongestEdge.start)
        side3 = distance(shortEdge.start, firstLongestEdge.end)
        side4 = distance(shortEdge.end, firstLongestEdge.end)
        if (edg.distance > span and side1 > span and side2 > span and
                side3 > span and side4 > span):
            shortestEdges.append(shortEdge)

    sorted_shortestEdges = sorted(shortestEdges,
                                  key=lambda x: x.distance,
                                  reverse=True)
    secondLongestEdge = sorted_shortestEdges[0]

    return [firstLongestEdge, secondLongestEdge]


def matchDirection(sett):
    """
        In this function we need to match the direction of edges to each other
        Suppos we have two edges that we know their are corresponding to
        each other between two mythologies but we do not know if in which direction.
        So we give them to this function, and this function will find the direction
        and correct it in the set. It works by finding the distance of each point of
        the edge from their corresponding center of mass of morphology,
        then comparing them together.
        Example: Suppose we have two edges of A and B. A and B each contains two
        points which we arbitrary will call them A_start, A_end, B_start, B_end.
        Now we calculate the center of mass of each morphology, suppose they are
        Center_A and Center_B. Since the edges A and B are corresponds to each other,
        thus, If for example point A_start is corresponds to point B_start and the
        distance of A_start to center_a is less than the distance of
        A_end to center_end, THEN the distance of B_start to center_b must also be
        less than the distance of B_end to center_b, otherwise we need to swap the
        points of B_start with B_end with each other to be match with A_start and A_end

    """

    centerOfSet1 = 0.0
    centerOfSet2 = 0.0
    length = len(sett)

    longestEdgCenter_A = (np.array(sett[0][0].start) +
                          np.array(sett[0][0].end)) / 2.0
    longestEdgCenter_B = (np.array(sett[0][1].start) +
                          np.array(sett[0][1].end)) / 2.0

    disA_start = distance(sett[1][0].start, longestEdgCenter_A)
    disB_start = distance(sett[1][1].start, longestEdgCenter_B)

    disA_end = distance(sett[1][0].end, longestEdgCenter_A)
    disB_end = distance(sett[1][1].end, longestEdgCenter_B)

    deltaA = disA_start - disA_end
    deltaB = disB_start - disB_end

    if (deltaA * deltaB < 0.0):
        tempStart = sett[1][1].start
        tempEnd = sett[1][1].end
        sett[1][1].end = tempStart
        sett[1][1].start = tempEnd

    second_longestEdgCenter_A = (np.array(sett[1][0].start) +
                                 np.array(sett[1][0].end)) / 2.0
    second_longestEdgCenter_B = (np.array(sett[1][1].start) +
                                 np.array(sett[1][1].end)) / 2.0

    second_disA_start = distance(sett[0][0].start, second_longestEdgCenter_A)
    second_disB_start = distance(sett[0][1].start, second_longestEdgCenter_B)

    second_disA_end = distance(sett[0][0].end, second_longestEdgCenter_A)
    second_disB_end = distance(sett[0][1].end, second_longestEdgCenter_B)

    deltaA_sec = second_disA_start - second_disA_end
    deltaB_sec = second_disB_start - second_disB_end

    if (deltaA_sec * deltaB_sec < 0.0):
        tempStart = sett[0][1].start
        tempEnd = sett[0][1].end
        sett[0][1].end = tempStart
        sett[0][1].start = tempEnd

    # for i in range(length):

    #     centerOfSet1 = centerOfSet1 + (np.array(sett[i][0].start) +
    #                                    np.array(sett[i][0].end))

    #     centerOfSet2 = centerOfSet2 + (np.array(sett[i][1].start) +
    #                                    np.array(sett[i][1].end))

    #     print("centerOfMass:")
    #     print(i)
    #     print(centerOfSet1)
    #     print(centerOfSet2)
    # centerOfSet1 = centerOfSet1/length
    # centerOfSet2 = centerOfSet2/length
    # print("centerOfMass:")
    # print(centerOfSet1)
    # print(centerOfSet2)

    # for i in range(length):

    #     deltaSet1 = distance(centerOfSet1, sett[i][0].start)\
    #         - distance(centerOfSet1, sett[i][0].end)

    #     deltaSet2 = distance(centerOfSet2, sett[i][1].start)\
    #         - distance(centerOfSet2, sett[i][1].end)

    #     startToCenter_set1 = distance(centerOfSet1, sett[i][0].start)
    #     endToCenter_set1 = distance(centerOfSet1, sett[i][0].end)

    #     startToCenter_set2 = distance(centerOfSet2, sett[i][1].start)
    #     endToCenter_set2 = distance(centerOfSet2, sett[i][1].end)

    #     if (startToCenter_set1 < endToCenter_set1 and startToCenter_set2 < endToCenter_set2):
    #         continue
    #     else:
    #         print("yessss")
    #         tempStart = sett[i][1].start
    #         tempEnd = sett[i][1].end
    #         sett[i][1].end = tempStart
    #         sett[i][1].start = tempEnd

    # print(deltaSet2)
    # if (deltaSet1*deltaSet2 < 0):
    #     print("yessssss")
    #     temp = sett[i][1].start
    #     sett[i][1].start = sett[i][1].end
    #     sett[i][1].end = temp

    return sett


def removeSameEdges(setEg, edg):
    """
    We do not use this function in the code, but this function will remove
    repeated edges in the set, We skip this function since,
    the function ""longestOptimalEdges" Will guaranty to not have such a problem

    """
    setEg.remove(edg)
    for el in setEg:
        if (edg.start == el.start or edg.start == el.end or
                edg.end == el.start or edg.end == el.end):
            setEg.remove(el)
    return setEg


def getMean(sett):
    '''Calculate the avarege length of all edges in an edges set'''
    mean = 0.
    for edg in sett:
        mean = mean + edg.distance

    mean = mean / len(sett)
    return mean


def matchEdges(setA, setB, m, spanFactor):
    """
    Function below will find mateched points between two sets of points
    the parameter m is indicating how many edges we want to match,
    notice each edges have two points

    """

    hullPointsA = findHullPoints(setA)
    hullPointsB = findHullPoints(setB)

    edgesA = constructEdges(hullPointsA)
    edgesB = constructEdges(hullPointsB)
    matchedSet = []

    longestEdgesA = longestOptimalEdges(edgesA, spanFactor)
    longestEdgesB = longestOptimalEdges(edgesB, spanFactor)

    A_firstLongestEdg = longestEdgesA[0]
    A_secondLongestEdg = longestEdgesA[1]

    B_firstLongestEdg = longestEdgesB[0]
    B_secondLongestEdg = longestEdgesB[1]

    matchedSet.append([A_firstLongestEdg, B_firstLongestEdg])
    matchedSet.append([A_secondLongestEdg, B_secondLongestEdg])

    directedMatchedSet = matchDirection(matchedSet)
    return directedMatchedSet
