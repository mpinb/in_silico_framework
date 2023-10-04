import numpy as np
import math as math
import collections

GRIDSIZE = np.array([50, 50, 50])
PRECISION = 3
EPS = 0.00001


def setGridSize(gridDescriptor):
    steps = gridDescriptor.split("-")
    for i in range(0, 3):
        value = steps[i]
        if(not float(value).is_integer()):
            raise RuntimeError("invalid grid step size {}".format(steps[i]))
        valueInt = int(value)
        GRIDSIZE[i] = valueInt


def getFloat(cubeId_xyz):
    parts = cubeId_xyz.split("_")
    xyzNum = np.zeros(3)
    for i in range(0, 3):
        xyzNum[i] = float(parts[i])
    return xyzNum


def gridDescriptorToInt(gridDescriptor):
    parts = gridDescriptor.split("-")
    return np.array([int(parts[0]), int(parts[1]), int(parts[2])])


def getCubeId(pos):
    vals = []
    for i in range(0, 3):
        r = pos[i]
        index = math.floor(r / GRIDSIZE[i])
        val = index * GRIDSIZE[i] + 0.5 * GRIDSIZE[i]
        if((0.5 * GRIDSIZE[i]).is_integer()):
            vals.append("{:.0f}".format(val))
        else:
            vals.append("{:.1f}".format(val))
    return "_".join(vals)


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


def getFloatFromXYZ(xyz):
    parts = xyz.split("_")
    return [float(parts[0]), float(parts[1]), float(parts[2])]


def getBox(centre):
    xLow = centre[0] - 0.5 * GRIDSIZE[0]
    xHigh = centre[0] + 0.5 * GRIDSIZE[0]
    yLow = centre[1] - 0.5 * GRIDSIZE[1]
    yHigh = centre[1] + 0.5 * GRIDSIZE[1]
    zLow = centre[2] - 0.5 * GRIDSIZE[2]
    zHigh = centre[2] + 0.5 * GRIDSIZE[2]
    return [xLow, xHigh, yLow, yHigh, zLow, zHigh]


def inBounds(X, box, strict = False):
    if(strict):
        return (X[:, 0] >= box[0]) & (X[:, 0] <= box[1]) & (X[:, 1] >= box[2]) & (X[:, 1] <= box[3]) & (X[:, 2] >= box[4]) & (X[:, 2] <= box[5])
    else:
        return (X[:, 0] >= box[0]) & (X[:, 0] < box[1]) & (X[:, 1] >= box[2]) & (X[:, 1] < box[3]) & (X[:, 2] >= box[4]) & (X[:, 2] < box[5])


def getTruncatedConeArea(height, radius1, radius2):
    radiusDiff = radius2 - radius1
    slantedHeight = math.sqrt(height*height + radiusDiff*radiusDiff)
    area = math.pi * (radius1 + radius2) * slantedHeight
    return area


def intersectPlane(plane, points):
    sides = []
    p0 = plane["position"]
    n = plane["normal"]
    for i in range(0, len(points)):
        x = points[i][0:3]
        det = np.dot(x-p0, n)
        if(det >= 0):
            sides.append(1)
        else:
            sides.append(-1)
    intersectionPoints = {}
    for i in range(1, len(points)):
        ia = i-1
        ib = i
        a = points[ia][0:3]
        b = points[ib][0:3]
        ra = points[ia][3]
        rb = points[ib][3]
        if(sides[ia] != sides[ib]):
            l = b - a
            ln = np.dot(l, n)
            if(ln != 0):
                d = np.dot(p0 - a, n) / ln
                q = a + d * l
                r = ra + d*(rb - ra)
                intersectionPoints[(ia, ib)] = {
                    "position": np.array([q[0], q[1], q[2], r])
                }
    return sides, intersectionPoints


def getCubeIndexFromDescriptor(cube):
    p = getFloatFromXYZ(cube)
    i = getCubeIndices(p)
    return (i[0], i[1], i[2])


def getCubeIndices(pos):
    I, R = np.divmod(pos[0:3], GRIDSIZE)    
    I = I.astype(int)
    B = (R == 0).astype(int)
    return (I[0], I[1], I[2], B[0], B[1], B[2])


def getCube(p):
    return np.floor_divide(p[0:3], GRIDSIZE)


def getPosFromIdx(idx):
    return np.array([idx[0]*GRIDSIZE[0], idx[1]*GRIDSIZE[1], idx[2]*GRIDSIZE[2]])


def getCubeTupleInt(i):
    return (int(i[0]), int(i[1]), int(i[2]))


def getCommonIndices(i1, i2):
    return (min(i1[0], i2[0]), min(i1[1], i2[1]), min(i1[2], i2[2]))


def getNextIntersectionPoint(p1, i1, p2, i2, k):
    i1_k = i1[k]
    i2_k = i2[k]
    b1_k = i1[k + 3]
    b2_k = i2[k + 3]    
    if(i1_k == i2_k or i1_k == i2_k - b2_k or i1_k - b1_k == i2_k):
        return None, None        
    diff_ik = i2_k - i1_k
    if(diff_ik == 1):
        iNew_k = i1_k + 1
    elif(diff_ik == -1):
        iNew_k = i1_k
    else:
        iNew_k = i1_k + diff_ik // 2    
    p1New_k = iNew_k * GRIDSIZE[k]
    q = (p1New_k - p1[k]) / (p2[k] - p1[k])
    pNew = p1 + q * (p2 - p1)
    pNew[k] = p1New_k    
    iNew = getCubeIndices(pNew)
    return pNew, iNew


def intersectPoints(p1, i1, p2, i2, k=0, depth=0):    
    nextDepth = depth+1
    if(depth > 900):        
        raise RuntimeError("Recursion depth {}".format(depth))
    pNew, iNew = getNextIntersectionPoint(p1, i1, p2, i2, k)    
    if(pNew is not None):        
        pointsLeft, indicesLeft = intersectPoints(p1, i1, pNew, iNew, k=0, depth=nextDepth)
        pointsRight, indicesRight = intersectPoints(pNew, iNew, p2, i2, k=0, depth=nextDepth)
        pointsLeft.extend(pointsRight)
        indicesLeft.extend(indicesRight)
        return pointsLeft, indicesLeft
    elif(k < 2):
        return intersectPoints(p1, i1, p2, i2, k+1, depth=nextDepth)
    else:        
        return [p2], [i2]


def getIntersectedEdgePoints(points):
    indices = []
    for p in points:
        indices.append(getCubeIndices(p))
    pointsIntersected = [points[0]]
    indicesIntersected = [indices[0]]
    for i in range(1, len(points)):
        p1 = points[i-1]
        idx1 = indices[i-1]
        p2 = points[i]
        idx2 = indices[i]
        pointsNew, indicesNew = intersectPoints(p1, idx1, p2, idx2)
        pointsIntersected.extend(pointsNew)
        indicesIntersected.extend(indicesNew)
    return pointsIntersected, indicesIntersected


def cubeInBounds(ixiyiz, boxMin, boxMax):
    cubeOrigin = np.multiply(ixiyiz, GRIDSIZE)
    return np.all((cubeOrigin >= boxMin) & (cubeOrigin < boxMax))


def pointsInBounds(points, boxMin, boxMax, strict=False):    
    pointsMin = np.min(points, axis=0)
    pointsMax = np.max(points, axis=0)
    return np.all(pointsMin[0:3] <= boxMax) and np.all(pointsMax[0:3] >= boxMin)


def indicesInBounds(cube, ixiyiz_min, ixiyiz_max):
    ixiyiz = np.array([cube[0], cube[1], cube[2]])
    return np.all(ixiyiz >= ixiyiz_min) and np.all(ixiyiz < ixiyiz_max)


def getClosest50MicronCube(ixiyiz):
    cubeCenter = np.multiply(ixiyiz, GRIDSIZE) + 0.5 * GRIDSIZE
    ixiyiz_50 = np.floor_divide(cubeCenter, np.array([50,50,50]))
    return (ixiyiz_50[0], ixiyiz_50[1], ixiyiz_50[2])


def getGridBounds(boxMin, boxMax):
    ixiyiz_min = getCubeIndices(boxMin)[0:3]
    ixiyiz_max = getCubeIndices(boxMax)[0:3]
    ixiyiz_delta = np.array([ixiyiz_max[0]-ixiyiz_min[0], ixiyiz_max[1]-ixiyiz_min[1], ixiyiz_max[2]-ixiyiz_min[2]])
    numCells = ixiyiz_delta[0] * ixiyiz_delta[1] * ixiyiz_delta[2]
    return {
        "boxMin" : boxMin,
        "boxMax" : boxMax,
        "ixiyiz_min" : ixiyiz_min,
        "ixiyiz_max" : ixiyiz_max,
        "ixiyiz_delta" : ixiyiz_delta,
        "numCells" : numCells
    }


def getArrayIndex(gridBounds, cube):    
    origin = gridBounds["ixiyiz_min"]
    gridRange = gridBounds["ixiyiz_delta"]
    nx = gridRange[0]
    ny = gridRange[1]
    ix = cube[0] - origin[0]
    iy = cube[1] - origin[1]
    iz = cube[2] - origin[2]
    if(ix < 0 or iy < 0 or iz < 0):
        raise RuntimeError("negative rel. index")
    idx = iz * nx * ny + iy * nx + ix
    if(idx >= gridBounds["numCells"]):
        raise RuntimeError("idx exceeds bounds")
    return idx


def getCubeFromArrayIndex(gridBounds, arrayIndex):
    origin = gridBounds["ixiyiz_min"]
    gridRange = gridBounds["ixiyiz_delta"]
    nx = gridRange[0]
    ny = gridRange[1]
    iz, rxy = np.divmod(arrayIndex, (nx * ny))
    iy, ix = np.divmod(rxy, nx)
    cx = int(ix + origin[0])
    cy = int(iy + origin[1])
    cz = int(iz + origin[2])
    return (cx, cy, cz)
