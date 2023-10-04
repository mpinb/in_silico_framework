import numpy as np


def getLayerDepths():
    name_depthRange = {}
    name_depthRange["L1"] = [0, 157]
    name_depthRange["L2"] = [157, 367]
    name_depthRange["L23"] = [157, 576]
    name_depthRange["L3"] = [367, 576]
    name_depthRange["L4"] = [576, 855]
    name_depthRange["L5A"] = [855, 1102]
    name_depthRange["L5B"] = [1102, 1349]
    name_depthRange["L5"] = [855, 1349]
    name_depthRange["L6A"] = [1349, 1620]
    name_depthRange["L6"] = [1349, 1973]
    return name_depthRange
    

def getLaminarLocations():
    return ["L1", "L23", "L4", "L5", "L6"]


def getColumns():
    return ["A1", "A2", "A3", "A4",
            "B1", "B2", "B3", "B4",
            "C1", "C2", "C3", "C4",
            "D1", "D2", "D3", "D4",
            "E1", "E2", "E3", "E4",
            "Alpha", "Beta", "Gamma", "Delta"]


def getRegionsForColumn(column, includeSurrounding = True):
    regions = [
        column,
        "S1_Septum_{}".format(column),
        "{}_Barreloid".format(column)
    ]
    if(includeSurrounding):
        regions.append("S1_Surrounding_{}".format(column))
    return regions


def getCellTypes(includeVPM = True):
    if(includeVPM):
        return ["L2PY", "L3PY", "L4PY", "L4sp", "L4ss",
                "L5IT", "L5PT", "L6CC", "L6INV", "L6CT", "INH", "VPM"]
    else:
        return ["L2PY", "L3PY", "L4PY", "L4sp", "L4ss",
                "L5IT", "L5PT", "L6CC", "L6INV", "L6CT", "INH"]


def getCellTypesExc(includeVPM = True):
    if(includeVPM):
        allCelltypes = getCellTypes(includeVPM=True)
        allCelltypes.remove("INH")
        return allCelltypes
    else:
        return getCellTypes()[0:10]


def getNetworkIndex(network):
    if(network == "RBC" or "Truncated" in network):
        return getNetworks().index(network)
    else:
        network = network.replace("-", "RBCTruncated")
        return getNetworks().index(network)


def getReferenceVolume():
    boxMin = np.array([-200, 300, -1000])
    boxMax = np.array([0, 500, 600])
    return boxMin, boxMax


def getL4Volume():    
    boxMin = np.array([-400, 100, -200])
    boxMax = np.array([200, 700, 150])
    return boxMin, boxMax


def getC2Volume():
    boxMin = np.array([-550, -50, -1400])
    boxMax = np.array([400, 850, 700])
    return boxMin, boxMax


def getC2VolumeExt():
    boxMin = np.array([-700, -200, -1600])
    boxMax = np.array([600, 1100, 800])
    return boxMin, boxMax


def getD2Volume():
    boxMin = np.array([-500, -500, -1600])
    boxMax = np.array([500, 500, 700])
    return boxMin, boxMax


def getCellularConnectivityVolume():
    boxMin = np.array([-700, -1200, -1600])
    boxMax = np.array([600, 1900, 800])
    return boxMin, boxMax


def getModelVolume():
    boxMin = np.array([-1600, -1200, -1600])
    boxMax = np.array([1800, 1900, 800])
    return boxMin, boxMax


def getSelectedCubeVolume():
    boxMin = np.array([-150, 250, 350])
    boxMax = np.array([-50, 350, 400])
    return boxMin, boxMax


def getReferenceVolumeL5():
    # grid size: 8 x 8 x 24
    boxMin = np.array([-128, 400, -408])
    boxMax = np.array([-48, 480, -360])
    return boxMin, boxMax

def getSelectedCellIds():
    # L5PT:  301854   (ct 6)
    # L2PY:  748854   (ct 0)
    # L6CC: 199678   (ct 7)
    return [301854, 748854, 199678]