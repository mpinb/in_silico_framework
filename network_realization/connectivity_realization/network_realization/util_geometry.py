import numpy as np
import math as math
import collections

GRIDSIZE = 50
PRECISION = 3
EPS = 0.00001


def isSamePoint(a, b):
    return np.linalg.norm(a-b) <= EPS


def getFloat(cubeId_xyz):
    parts = cubeId_xyz.split("_")
    xyzNum = np.zeros(3)
    for i in range(0, 3):
        xyzNum[i] = float(parts[i])
    return xyzNum


def getCubeId(pos):
    cubeId = ""
    for i in range(0, 3):
        r = pos[i]
        index = math.floor(r / GRIDSIZE)
        cubeId += str(int(index * GRIDSIZE + 0.5 * GRIDSIZE))
        if(i < 2):
            cubeId += "_"
    return cubeId


def getBorderingCubeIds(position):
    cubeId = getCubeId(position)
    initial_xyz = getFloat(cubeId)
    xCoords = [initial_xyz[0]]
    yCoords = [initial_xyz[1]]
    zCoords = [initial_xyz[2]]
    borderingCubes = []
    for i in range(0, 3):
        coord = position[i]
        frac = coord / GRIDSIZE
        if(frac.is_integer()):
            newCoord = initial_xyz[i] - GRIDSIZE
            if(i == 0):
                xCoords.append(newCoord)
            elif(i == 1):
                yCoords.append(newCoord)
            else:
                zCoords.append(newCoord)
    for x in xCoords:
        for y in yCoords:
            for z in zCoords:
                newId = "_".join([str(int(x)), str(int(y)), str(int(z))])
                if(newId != cubeId):
                    borderingCubes.append(newId)
    return borderingCubes


def loadGrid(gridFilePath):
    cubeId_xyz = {}
    xyz_cubeId = {}
    with open(gridFilePath) as f:
        lines = f.readlines()
        for line in lines:
            parts = line.rstrip().split(" ")
            id = parts[0]
            xyz = "_".join(parts[1:4])
            cubeId_xyz[id] = xyz
            xyz_cubeId[xyz] = id
    return cubeId_xyz, xyz_cubeId


def getMinMax(xyz1, xyz2):
    xyzInt1 = getIntFromXYZ(xyz1)
    xyzInt2 = getIntFromXYZ(xyz2)
    xyzMin = []
    xyzMax = []
    for i in range(0, 3):
        if(xyzInt1[i] <= xyzInt2[i]):
            xyzMin.append(xyzInt1[i])
            xyzMax.append(xyzInt2[i])
        else:
            xyzMin.append(xyzInt2[i])
            xyzMax.append(xyzInt1[i])
    return xyzMin, xyzMax


def getNeighbouringCubes(xyz1, xyz2):
    xyzMin, xyzMax = getMinMax(xyz1, xyz2)
    neighbouringCubes = []
    for x in range(xyzMin[0], xyzMax[0] + 1, GRIDSIZE):
        for y in range(xyzMin[1], xyzMax[1] + 1, GRIDSIZE):
            for z in range(xyzMin[2], xyzMax[2] + 1, GRIDSIZE):
                xyz = "_".join([str(x), str(y), str(z)])
                neighbouringCubes.append(xyz)
    return neighbouringCubes


def getIntFromXYZ(xyz):
    parts = xyz.split("_")
    return [int(parts[0]), int(parts[1]), int(parts[2])]


def getFloatFromXYZ(xyz):
    parts = xyz.split("_")
    return [float(parts[0]), float(parts[1]), float(parts[2])]


def getBox(centre):
    xLow = centre[0] - 25
    xHigh = centre[0] + 25
    yLow = centre[1] - 25
    yHigh = centre[1] + 25
    zLow = centre[2] - 25
    zHigh = centre[2] + 25
    return [xLow, xHigh, yLow, yHigh, zLow, zHigh]


def clipLine(p0, p1, box):
    """
    Clip a line segment defined by @c p0 and @c p1 against the box.
    This method uses the Liang-Barsky clipping algorithm.
    @returns true if the line segment intersects the box. 
    In this case,  @c q0 and @c q1 hold the intersection points 
    of the segment with the box.
    """
    t0 = 0
    t1 = 1

    q0 = [p0[0], p0[1], p0[2]]
    q1 = [p1[0], p1[1], p1[2]]

    Dx = q1[0] - q0[0]
    t0, t1 = LiangBarskyClipTest(-Dx, q0[0] - box[0], t0, t1)
    if (t0 != -99):
        t0, t1 = LiangBarskyClipTest(Dx, box[1] - q0[0], t0, t1)
        if (t0 != -99):
            Dy = q1[1] - q0[1]
            t0, t1 = LiangBarskyClipTest(-Dy, q0[1] - box[2], t0, t1)
            if (t0 != -99):
                t0, t1 = LiangBarskyClipTest(Dy, box[3] - q0[1], t0, t1)
                if (t0 != -99):
                    Dz = q1[2] - q0[2]
                    t0, t1 = LiangBarskyClipTest(-Dz, q0[2] - box[4], t0, t1)
                    if (t0 != -99):
                        t0, t1 = LiangBarskyClipTest(
                            Dz, box[5] - q0[2], t0, t1)
                        if (t0 != -99):
                            hits = []
                            if (t0 > 0 and t0 < 1):
                                q0[0] = p0[0] + t0 * Dx
                                q0[1] = p0[1] + t0 * Dy
                                q0[2] = p0[2] + t0 * Dz
                                hits.append(np.array([round(float(q0[0]), 3), round(
                                    float(q0[1]), 3), round(float(q0[2]), 3)]))
                            if (t1 > 0 and t1 < 1):
                                q1[0] = p0[0] + t1 * Dx
                                q1[1] = p0[1] + t1 * Dy
                                q1[2] = p0[2] + t1 * Dz
                                hits.append(np.array([round(float(q1[0]), 3), round(
                                    float(q1[1]), 3), round(float(q1[2]), 3)]))
                            return hits
    return []


def LiangBarskyClipTest(p, q, t0, t1):
    if (p < 0):
        t = q / p
        if (t > t1):
            return [-99, -99]
        if (t > t0):
            t0 = t
    elif (p > 0):
        t = q / p
        if (t < t0):
            return [-99, -99]
        if (t < t1):
            t1 = t
    elif (q < 0):
        return [-99, -99]
    return [t0, t1]


def sortImPoints(edgePoint1, imPoints):
    imPointsSortedDist = sorted(imPoints, key=lambda imPoint: np.linalg.norm(
        imPoint["position"] - edgePoint1["position"]))
    return imPointsSortedDist


def mergeImPoints(imPoints, ep1, ep2, neuronId):
    if(len(imPoints) % 2 != 0):
        print("no multiple of 2", neuronId, ep1, ep2)
        for imP in imPoints:
            print(imP)
        raise RuntimeError("none or isolated intermediate point")
    merged = []
    for i in range(0, len(imPoints), 2):
        a = imPoints[i]
        posA = imPoints[i]["position"]
        posB = imPoints[i+1]["position"]
        if(not isSamePoint(posA, posB)):
            print("failed merging", i, imPoints)
            raise RuntimeError("failed merging intermediate points")
        merged.append(a)
    return merged


def getIntersectionPoints(edgePoint1, edgePoint2, neuronId):
    edgeId = edgePoint1["edge_id"]
    sourceNodeId = edgePoint1["source_node_id"]
    targetNodeId = edgePoint1["target_node_id"]
    edgeLabel = edgePoint1["edge_label"]

    pos1 = edgePoint1["position"]
    pos2 = edgePoint2["position"]
    rad1 = edgePoint1["radius"]
    rad2 = edgePoint2["radius"]
    cubeId1 = edgePoint1["cubeId"]
    cubeId2 = edgePoint2["cubeId"]

    cubeIds = getNeighbouringCubes(cubeId1, cubeId2)
    imPoints = []
    for cubeId in cubeIds:
        box = getBox(getIntFromXYZ(cubeId))
        hits = clipLine(pos1, pos2, box)
        for hit in hits:
            imPoint = {}
            imPoint["edge_id"] = edgeId
            imPoint["source_node_id"] = sourceNodeId
            imPoint["target_node_id"] = targetNodeId
            imPoint["edge_label"] = edgeLabel
            imPoint["edge_point_id"] = -1
            imPoint["cubeId"] = getCubeId(hit)
            imPoint["borderingCubeIds"] = getBorderingCubeIds(hit)
            imPoint["position"] = hit
            imPoint["radius"] = interpolateRadius(pos1, rad1, pos2, rad2, hit)
            imPoint["inside_vS1"] = 1

            # if(imPoint["cubeId"] in ["-175_325_-675", "-175_325_-625"]):
            #    print(imPoint)
            imPoints.append(imPoint)

    imPointsSorted = sortImPoints(edgePoint1, imPoints)
    imPointsMerged = mergeImPoints(
        imPointsSorted, edgePoint1, edgePoint2, neuronId)
    return imPointsMerged


def insertIntersectionPoints(edgePoints, neuronId):
    expanded = []
    for i in range(1, len(edgePoints)):
        edgePoint1 = edgePoints[i-1]
        edgePoint2 = edgePoints[i]
        cubeId1 = edgePoint1["cubeId"]
        cubeId2 = edgePoint2["cubeId"]
        expanded.append(edgePoint1)
        if(cubeId1 != cubeId2):
            intersectionPoints = getIntersectionPoints(
                edgePoint1, edgePoint2, neuronId)
            expanded.extend(intersectionPoints)
    expanded.append(edgePoints[-1])
    return expanded


def separateEdges(edgePoints):
    edges = collections.OrderedDict()
    for i in range(0, len(edgePoints)):
        point = edgePoints[i]
        edges[point["edge_id"]] = []
    for point in edgePoints:
        edges[point["edge_id"]].append(point)
    return edges


def applyGrid(id, edgePoints):
    for ep in edgePoints:
        position = ep["position"]
        ep["cubeId"] = getCubeId(position)
        ep["borderingCubeIds"] = getBorderingCubeIds(position)
    edgePointsIntersected = []
    edges = separateEdges(edgePoints)
    for edgeId, raw in edges.items():
        intersected = insertIntersectionPoints(raw, id)
        edgePointsIntersected.extend(intersected)
    return edgePointsIntersected


def getEmptyFeatures():
    features = {}
    features["bbMin"] = np.zeros(3)
    features["bbMax"] = np.zeros(3)
    features["bbExtent"] = np.zeros(3)
    features["centerOfMass"] = np.zeros(3)
    return features


def getGeometricalFeatures(points):
    features = getEmptyFeatures()
    if(points.shape[0] == 0):
        return features
    bbMin = np.amin(points, axis=0)
    bbMax = np.amax(points, axis=0)
    centerOfMass = np.mean(points, axis=0)
    features["bbMin"] = bbMin
    features["bbMax"] = bbMax
    features["bbExtent"] = bbMax - bbMin
    features["centerOfMass"] = centerOfMass
    return features


def toInt(x):
    return int(x)


def toFloat(x):
    return float(x)


def loadGridSpec(gridFile):
    props = {}
    with open(gridFile) as f:
        lines = f.readlines()
        props["dimensions"] = list(
            map(toInt, lines[0].rstrip().split(",")[1:]))
        props["origin"] = list(map(toFloat, lines[1].rstrip().split(",")[1:]))
        props["spacing"] = list(map(toFloat, lines[2].rstrip().split(",")[1:]))
    return props


def cxcycz_ixiyiz(gridSpec, cxcycz):
    origin = gridSpec["origin"]
    spacing = gridSpec["spacing"]
    dimensions = gridSpec["dimensions"]
    ixiyiz = []
    for i in range(0, 3):
        k = int(math.floor(float(cxcycz[i]) - float(origin[i]))/spacing[i])
        if(k >= dimensions[i]):
            raise RuntimeError("grid bounds " + str(cxcycz))
        ixiyiz.append(k)
    return ixiyiz


def ixiyiz_cxcyczString(gridSpec, ixiyiz):
    origin = gridSpec["origin"]
    spacing = gridSpec["spacing"]
    dimensions = gridSpec["dimensions"]
    ixiyizParts = ixiyiz.split("_")
    cxcycz = []
    for i in range(0, 3):
        cxcycz.append(int(origin[i] + int(ixiyizParts[i])
                          * spacing[i] + 0.5 * spacing[i]))
    return "{0}_{1}_{2}".format(*cxcycz)


def interpolateRadius(p0, r0, p1, r1, targetPos):
    totalLen = np.linalg.norm(p1-p0)
    if(math.fabs(totalLen) < 0.0001):
        return 0.5 * (r0 + r1)
    p0targetLen = np.linalg.norm(targetPos-p0)
    alpha = p0targetLen / totalLen
    return alpha*r1 + (1-alpha)*r0


def getTruncatedConeArea(height, radius1, radius2):
    radiusDiff = radius2 - radius1
    slantedHeight = math.sqrt(height*height + radiusDiff*radiusDiff)
    area = math.pi * (radius1 + radius2) * slantedHeight
    return area
