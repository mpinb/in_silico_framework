import numpy as np


def getTransformation(src, dst):
    """
    This function will calculate the affien transformation matrix from
    8 points (4 source poitns and 4 destination points)

    """
    x = np.transpose(np.matrix([src[0], src[1], src[2], src[3]]))
    y = np.transpose(np.matrix([dst[0], dst[1], dst[2], dst[3]]))

    # add ones on the bottom of x and y
    x = np.matrix(np.vstack((x,[1.0,1.0,1.0,1.0])))
    y = np.matrix(np.vstack((y,[1.0,1.0,1.0,1.0])))
    # solve for A2

    trMatrix = y * x.I
    print(trMatrix)
    return trMatrix


def applyTransformationMatrix(points, matrix):
    """
    transforms the first 3 coordinates of the points. 
    """
    trAmPoints4D = []
    for point4D in points:
        point = point4D[:3]
        mPoint = np.matrix(point)
        mTrPoint = mPoint.T
        p = matrix*np.matrix(np.vstack((mTrPoint, 1.0)))
        p = np.array(p.T)
        p_listed = p.tolist()[0]
        # raw_input("somet")
        trAmPoints4D.append(p_listed[0:3] + point4D[3:])

    return trAmPoints4D
