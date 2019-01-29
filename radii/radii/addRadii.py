
import transformTools as tr


def findNextPair(trPoints, hocPoint):
    dual = trPoints[0]
    minDistance = tr.getDistance.distance2(dual[:4], hocPoint)
    for newPoint in trPoints:
        # print("please Point:", newPoint)
        dist = tr.getDistance.distance2(newPoint[:4], hocPoint)
        # print("2nd please Point:", newPoint)
        if dist <= minDistance:
            minDistance = dist
            dual = newPoint
    return dual


def filterPoints(transformedPoints, hocPoints, observerIndex):
    trP = transformedPoints
    preIdx = observerIndex - 1
    nextIdx = observerIndex + 1
    p_0 = hocPoints[preIdx]
    p_1 = hocPoints[nextIdx]
    delta = 50.0

    # Cartesian calculations:

    if p_0[0] < p_1[0]:
        x_start = p_0[0] - delta
        x_end = p_1[0] + delta
    else:
        x_start = p_1[0] - delta
        x_end = p_0[0] + delta

    if p_0[1] < p_1[1]:
        y_start = p_0[1] - delta
        y_end = p_1[1] + delta
    else:
        y_start = p_1[1] - delta
        y_end = p_0[1] + delta

    if p_0[2] < p_1[2]:
        z_start = p_0[2] - delta
        z_end = p_1[2] + delta
    else:
        z_start = p_1[2] - delta
        z_end = p_0[2] + delta

    subSet = [p for p in trP if (x_start <= p[0] and p[0] <= x_end) and
              (y_start <= p[1] and p[1] <= y_end) and (z_start <= p[2] and p[2] <= z_end)]

    #Spherical Calculations:

    # center = hocPoints[observerIndex]
    # nextP = hocPoints[nextIdx]
    # initRad = 2*tr.getDistance.distance(center, nextP) + delta
    # initRad2 = initRad**2
    # letItGo = False
    # rad2 = initRad2
    # factor = 1
    # while (letItGo is not True):
    #     subSet = [p for p in trP if ((p[0]-center[0])**2 +
    #                                 (p[1]-center[1])**2 +
    #                                 (p[2]-center[2])**2 <= rad2)]

    #     if (subSet != []):
    #         letItGo = True
    #         return subSet
    #     factor = factor*10
    #     rad2 = factor**2*rad2

    return subSet


def findPairs(transformedPoints, hocPoints):
    hocFirstPoint = hocPoints[0]
    dualPair = findNextPair(transformedPoints, hocFirstPoint)
    pairs = []
    pairs.append([dualPair, hocFirstPoint])

    for hIdx, hPoint in enumerate(hocPoints[1:]):
        subTransformedPoints = filterPoints(transformedPoints, hocPoints, hIdx)
        if (subTransformedPoints != []):
            # print("in the subTransformedPoints:", "processed points:", hIdx, "length of subSet", len(subTransformedPoints) )
            dualPair = findNextPair(subTransformedPoints, hPoint)
            pairs.append([dualPair, hPoint])
            # transformedPoints = [x for x in transformedPoints if x not in subTransformedPoints]
        else:
            dualPair = findNextPair(transformedPoints, hPoint)
            pairs.append([dualPair, hPoint])

    return pairs
