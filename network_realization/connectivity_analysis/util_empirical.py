import sys
import os
import json
from functools import cmp_to_key

import constants
import util_citations


def loadPublications(filename, extend_sort = False):
    with open(filename) as f:
        publications = json.load(f)
    if(extend_sort):
        for publication in publications:
            selectionDescriptor = getSelectionDescriptor(publication)
            publication["selection_descriptor"] = selectionDescriptor            
            publication["first_author_year"] = getFirstAuthorYearDescriptor(publication)
        sortPublications(publications)   
    return publications


def loadSelectionIndex(filename):
    with open(filename) as f:
        data = json.load(f)
        return data


def sortPublications(publications):
    publications.sort(key=cmp_to_key(cmpFunction))


def cmpLayer(a, b):
    if(a == "VPM" and b != "VPM"):
        return -1
    elif(a != "VPM" and b == "VPM"):
        return 1
    elif(a < b):
        return -1
    elif(a > b):
        return 1
    else:
        return 0


def cmpCellType(a, b):
    cellTypes = constants.getCellTypes()
    cellTypes.insert(0, "EXC")
    if(cellTypes.index(a) < cellTypes.index(b)):
        return -1
    elif(cellTypes.index(a) > cellTypes.index(b)):
        return 1
    else:
        return 0


def cmpScalar(a, b):
    if(a < b):
        return -1
    elif(a > b):
        return 1
    else:
        return 0


def cmpFunction(a, b):
    preLayer = cmpLayer(a["pre_layer"], b["pre_layer"])
    postLayer = cmpLayer(a["post_layer"], b["post_layer"])
    preCellType = cmpCellType(a["pre_type"], b["pre_type"])
    postCellType = cmpCellType(a["post_type"], b["post_type"])
    year = cmpScalar(a["year"], b["year"])
    probability = cmpScalar(a["cp_empirical"], b["cp_empirical"])

    if(a["ID"] == b["ID"]):
        return 0
    elif(preLayer != 0):
        return preLayer
    elif(preCellType != 0):
        return preCellType
    elif(postLayer != 0):
        return postLayer
    elif(postCellType != 0):
        return postCellType
    elif(year != 0):
        return year
    elif(probability != 0):
        return probability
    else:
        return 0


def getSelectionDescriptor(publication):
    measurementType = publication["type"]
    if(measurementType == "connection_probability_invivo"):
        invivo_invitro = "invivo"
    elif(measurementType == "connection_probability_invitro"):
        invivo_invitro = "invitro"
    else:
        raise RuntimeError(
            "unknown measurement type {}".format(measurementType))
    descriptor = "{}_{}-{}-->{}-{}".format(
        invivo_invitro, publication["pre_layer"], publication["pre_type"], publication["post_layer"], publication["post_type"])
    if(publication["only_septum"] == "yes"):
        descriptor += "-septum"
    return descriptor


def getFirstAuthorYearDescriptor(publication):
    author = util_citations.getFirstAuthorLastName(publication["authors"])
    return "{} et al. {}".format(author, publication["year"])


def filterInvivo(publications):
    publicationsFiltered = []
    for publication in publications:
        if(publication["type"] == "connection_probability_invivo"):
            publicationsFiltered.append(publication)
    return publicationsFiltered


def filterInvivoVPM(publications):
    publicationsFiltered = []
    for publication in publications:
        if(publication["type"] == "connection_probability_invivo" and publication["pre_type"] == "VPM"):
            publicationsFiltered.append(publication)
    return publicationsFiltered


def filterInvitro(publications):
    publicationsFiltered = []
    for publication in publications:
        if(publication["type"] == "connection_probability_invitro"):
            publicationsFiltered.append(publication)
    return publicationsFiltered


def filterByIds(publications, ids):
    if(not len(ids)):
        return publications
    publicationsFiltered = []
    for publication in publications:
        if(publication["ID"] in ids):
            publicationsFiltered.append(publication)
    return publicationsFiltered


def getPublication(publications, id):
    for publication in publications:
        if(id == publication["ID"]):
            return publication
    raise RuntimeError("ID not found {}".format(id))


def printUsageAndExit():
    print("util_empirical.py <mode> <file-default> <file-extended>")
    print()
    print("mode:    write-extended")
    exit(0)


if __name__ == "__main__":
    if(len(sys.argv) != 4):
        printUsageAndExit()
    mode = sys.argv[1]
    if(mode not in ["write-extended"]):
        printUsageAndExit()
    
    if(mode == "write-extended"):
        publications = loadPublications(sys.argv[2], extend_sort=True)
        with open(sys.argv[3], "w+") as f:
            json.dump(publications, f)
