import os
import collections
import numpy as np


def getSpec_subcellular_features_postsynaptic():
    labels = [
        "length_soma",
        "length_apical",
        "length_basal",
        "area_soma",
        "area_apical",
        "area_basal",
        "pst_exc_soma",
        "pst_exc_apical",
        "pst_exc_basal",
        "pst_inh_soma",
        "pst_inh_apical",
        "pst_inh_basal",
        "branchlets",
        "path_distance_soma_apical",
        "path_distance_soma_basal",
        "path_distance_soma",
        "bifurcations_apical",
        "bifurcations_basal",
        "bifurcations_dendrite",
        "distance_soma",
        "distance_dendrites_center_of_mass",
        "distance_main_bifurcation",
        "path_distance_main_bifurcation",
    ]
    defaults = {
        "length_soma": 0,
        "length_apical": 0,
        "length_basal": 0,
        "area_soma": 0,
        "area_apical": 0,
        "area_basal": 0,
        "pst_exc_soma": 0,
        "pst_exc_apical": 0,
        "pst_exc_basal": 0,
        "pst_inh_soma": 0,
        "pst_inh_apical": 0,
        "pst_inh_basal": 0,
        "branchlets": 0,
        "path_distance_soma_apical": -1,
        "path_distance_soma_basal": -1,
        "path_distance_soma": -1,
        "bifurcations_apical": 0,
        "bifurcations_basal": 0,
        "bifurcations_dendrite": 0,
        "distance_soma": -1,
        "distance_dendrites_center_of_mass": -1,
        "distance_main_bifurcation": -1,
        "path_distance_main_bifurcation": -1,
    }
    decimalDigits = {
        "length_soma": 6,
        "length_apical": 6,
        "length_basal": 6,
        "area_soma": 6,
        "area_apical": 6,
        "area_basal": 6,
        "pst_exc_soma": 6,
        "pst_exc_apical": 6,
        "pst_exc_basal": 6,
        "pst_inh_soma": 6,
        "pst_inh_apical": 6,
        "pst_inh_basal": 6,
        "branchlets": 0,
        "path_distance_soma_apical": 6,
        "path_distance_soma_basal": 6,
        "path_distance_soma": 6,
        "bifurcations_apical": 0,
        "bifurcations_basal": 0,
        "bifurcations_dendrite": 0,
        "distance_soma": 6,
        "distance_dendrites_center_of_mass": 6,
        "distance_main_bifurcation": 6,
        "path_distance_main_bifurcation": 6,
    }
    specs = {
        "labels": labels,
        "defaults": defaults,
        "decimalDigits": decimalDigits
    }
    return specs


def getSpec_subcellular_features_postsynaptic_sparse():
    labels = [
        "pst_exc_soma",
        "pst_exc_apical",
        "pst_exc_basal",
        "pst_inh_soma",
        "pst_inh_apical",
        "pst_inh_basal"
    ]
    defaults = {
        "pst_exc_soma": 0,
        "pst_exc_apical": 0,
        "pst_exc_basal": 0,
        "pst_inh_soma": 0,
        "pst_inh_apical": 0,
        "pst_inh_basal": 0
    }
    decimalDigits = {
        "pst_exc_soma": 6,
        "pst_exc_apical": 6,
        "pst_exc_basal": 6,
        "pst_inh_soma": 6,
        "pst_inh_apical": 6,
        "pst_inh_basal": 6
    }
    specs = {
        "labels": labels,
        "defaults": defaults,
        "decimalDigits": decimalDigits
    }
    return specs


def getSpec_subcellular_features_postsynaptic_length():
    labels = [
        "length_apical",
        "length_basal",
    ]
    defaults = {
        "length_apical": 0,
        "length_basal": 0,
    }
    decimalDigits = {        
        "length_apical": 6,
        "length_basal": 6,
    }
    specs = {
        "labels": labels,
        "defaults": defaults,
        "decimalDigits": decimalDigits
    }
    return specs



def getSpec_subcellular_features_presynaptic():
    labels = ["length_axon",
              "boutons",
              "branchlets"
              ]
    defaults = {
        "length_axon": 0,
        "boutons": 0,
        "branchlets": 0
    }
    decimalDigits = {
        "length_axon": 6,
        "boutons": 6,
        "branchlets": 0
    }
    specs = {
        "labels": labels,
        "defaults": defaults,
        "decimalDigits": decimalDigits
    }
    return specs


def getSpec_agg_pst():
    labels = ["pst_exc",
              "pst_inh"]
    defaults = {
        "pst_exc": 0,
        "pst_inh": 0
    }
    decimalDigits = {
        "pst_exc": 6,
        "pst_inh": 6
    }
    specs = {
        "labels": labels,
        "defaults": defaults,
        "decimalDigits": decimalDigits
    }
    return specs


def formatNumber(val, decimalDigits):
    return str(round(val, decimalDigits))


def writeFeatures(filename, spec, data):
    labels = spec["labels"]
    defaults = spec["defaults"]
    decimalDigits = spec["decimalDigits"]
    with open(filename, "w+") as f:
        f.write("subvolume," + ",".join(labels) + "\n")
        for subvolume, features in data.items():
            values = []
            decimals = []
            for label in labels:
                decimals.append(decimalDigits[label])
                if(label in features.keys()):
                    values.append(features[label])
                else:
                    values.append(defaults[label])
            dataFormatted = map(
                lambda x, d: formatNumber(x, d), values, decimals)
            f.write(str(subvolume) + "," + ",".join(dataFormatted) + "\n")



def writeAxonFeatures(filename, data):
    with open(filename, "w+") as f:
        f.write("ix,iy,iz,ib,length,boutons,distance_soma\n")
        for cube, branches in data.items():
            for ib, values in branches.items():
                f.write("{:.0f},{:.0f},{:.0f},{},{:.4f},{:.4f},{:.1f}\n".format(cube[0], cube[1], cube[2], ib, values["length"], values["boutons"], np.min(values["distSoma"])))


def readAxonFeaturesForDSC(filename):    
    if(not os.path.exists(filename)):
        return None
    data = {}
    with open(filename) as f:
        lines = f.readlines()
        for i in range(1,len(lines)):
            parts = lines[i].rstrip().split(",")
            cube = (int(parts[0]), int(parts[1]) , int(parts[2]))            
            if(cube not in data):
                data[cube] = 0
            data[cube] += float(parts[5]) # boutons
    return data


def writeDendriteFeatures(filename, data):
    with open(filename, "w+") as f:
        f.write("ix,iy,iz,branch,length,pstExc,pstInh,distance_soma\n")
        for cube, branches in data.items():            
            for branch, values in branches.items():
                f.write("{:.0f},{:.0f},{:.0f},{},{:.4f},{:.4f},{:.4f},{:.1f}\n".format(cube[0], cube[1], cube[2], branch, values["length"], values["pstExc"], values["pstInh"], np.min(values["distSoma"])))


def readDendriteFeatures(filename):    
    if(not os.path.exists(filename)):
        return None
    data = {}
    with open(filename) as f:
        lines = f.readlines()
        for i in range(1,len(lines)):
            parts = lines[i].rstrip().split(",")
            cube = (int(parts[0]), int(parts[1]) , int(parts[2]))            
            if(cube not in data):
                data[cube] = []        
            data[cube].append({
                "length" : float(parts[4]),
                "pstExc" : float(parts[5]),
                "pstInh" : float(parts[6]),
                "distSoma": float(parts[7])
            })
    return data


def getCubesFromFeatures(filename):
    if(not os.path.exists(filename)):
        return None
    cubes = set()
    with open(filename) as f:
        lines = f.readlines()
        for i in range(1,len(lines)):
            parts = lines[i].rstrip().split(",")
            cube = (int(parts[0]), int(parts[1]) , int(parts[2]))
            cubes.add(cube)
    return cubes


def readBoutonsPerCube(filename, allowedCubes):
    if(not os.path.exists(filename)):
        return None
    data = {}
    with open(filename) as f:
        lines = f.readlines()
        for i in range(1,len(lines)):
            parts = lines[i].rstrip().split(",")
            cube = (int(parts[0]), int(parts[1]) , int(parts[2]))
            if(not allowedCubes or cube in allowedCubes):
                boutons = float(parts[5])
                if(boutons):
                    if(cube not in data):
                        data[cube] = 0
                    data[cube] += boutons
    return data


def readBoutonsPerCubeDebug(filename, allowedCubes):
    if(not os.path.exists(filename)):
        return None
    data = {}
    with open(filename) as f:
        lines = f.readlines()
        for i in range(1,len(lines)):
            parts = lines[i].rstrip().split(",")
            cube = (int(parts[0]), int(parts[1]) , int(parts[2]))
            if(not allowedCubes or cube in allowedCubes):
                boutons = float(parts[5])                
                if(cube not in data):
                    data[cube] = 0
                data[cube] += boutons
    return data


def readAxonFeatures(filename):    
    if(not os.path.exists(filename)):
        return None
    data = {}
    with open(filename) as f:
        lines = f.readlines()
        for i in range(1,len(lines)):
            parts = lines[i].rstrip().split(",")
            cube = (int(parts[0]), int(parts[1]) , int(parts[2]))            
            if(cube not in data):
                data[cube] = []        
            data[cube].append({
                "length" : float(parts[4]),
                "boutons" : float(parts[5]),                
                "distSoma": float(parts[6])
            })
    return data


def writeCubeIndex(filename, data):
    with open(filename, "w+") as f:
        f.write("nid,pst_exc,pst_inh\n")
        for values in data:
            f.write("{},{:.4f},{:.4f}\n".format(values[0],values[1],values[2]))


def writeCubeIndexPre(filename, data):
    with open(filename, "w+") as f:
        f.write("nid,boutons\n")
        for values in data:
            f.write("{},{:.4f}\n".format(values[0],values[1]))


def loadFeatures(filename, spec):
    data = collections.OrderedDict()
    with open(filename) as f:
        lines = f.readlines()
        header = lines[0].rstrip().split(",")
        for i in range(1, len(lines)):
            line = lines[i].rstrip().split(",")
            decimalDigits = spec["decimalDigits"]
            values = {}
            for label in spec["labels"]:
                if(decimalDigits[label]):
                    values[label] = float(line[header.index(label)])
                else:
                    values[label] = int(line[header.index(label)])
            data[int(line[header.index("subvolume")])] = values
    return data


def write_DSC(filename, DSC):
    with open(filename, "w+") as f:
        f.write("post_id,subvolume,DSC_soma,DSC_apical,DSC_basal\n")
        for postId, values in DSC.items():
            for subvolume, DSC in values.items():
                f.write("{:d},{:d},{:.6f},{:.6f},{:.6f}\n".format(
                    postId, subvolume, DSC["soma"], DSC["apical"], DSC["basal"]))


def load_DSC(filename):
    with open(filename) as f:
        data = collections.OrderedDict()
        lines = f.readlines()
        for i in range(1, len(lines)):
            line = lines[i].rstrip().split(",")
            postId = int(line[0])
            subvolume = int(line[1])
            DSC_soma = float(line[2])
            DSC_apical = float(line[3])
            DSC_basal = float(line[4])
            if(postId not in data.keys()):
                data[postId] = collections.OrderedDict()
            data[postId][subvolume] = {
                "soma": DSC_soma,
                "apical": DSC_apical,
                "basal": DSC_basal,
            }
        return data


def write_agg_DSC(filename, agg_DSC):
    with open(filename, "w+") as f:
        f.write("post_id,DSC_soma,DSC_apical,DSC_basal\n")
        for postId, values in agg_DSC.items():
            f.write("{:d},{:.6f},{:.6f},{:.6f}\n".format(
                postId, values["soma"], values["apical"], values["basal"]))


def load_agg_DSC(filename):
    with open(filename) as f:
        lines = f.readlines()
        data = collections.OrderedDict()
        for i in range(1, len(lines)):
            line = lines[i].rstrip().split(",")
            values = {}
            values["soma"] = float(line[1])
            values["apical"] = float(line[2])
            values["basal"] = float(line[3])
            data[int(line[0])] = values
        return data


def load_agg_pst(filename):
    return loadFeatures(filename, getSpec_agg_pst())


def load_agg_pst_flat(filename, excitatory):
    pstAll = load_agg_pst(filename)    
    pstAllPruned = {}
    if(excitatory):
        label = "pst_exc"
    else:
        label = "pst_inh"
    for cubeId, props  in pstAll.items():
        pstAllPruned[cubeId] = props[label]
    return pstAllPruned


def writeCellularFeaturesBlockFormat(filename, features, labels, mode="cellular"):
    with open(filename, "w+") as f:
        f.write("\t".join(labels) + "\n")
        for i in range(0, len(features)):
            entry = features[i]
            if(mode == "cellular"):
                f.write("{}\t{}\t{}".format(int(entry[0]), int(entry[1]), int(entry[2])))
                for j in range(3, len(entry)):
                    f.write("\t{:.5f}".format(entry[j]))
            elif(mode == "subcellular"):
                f.write("{}\t{}\t{}\t{}".format(int(entry[0]), int(entry[1]), int(entry[2]), int(entry[3])))
                for j in range(4, len(entry)):
                    f.write("\t{:.1f}".format(entry[j]))
            else:
                raise RuntimeError("invalid mode: {}".format(mode))
            f.write("\n")


def readCellularFeaturesBlockFormat(filename, mode="cellular"):
    with open(filename) as f:
        lines = f.readlines()
        if(mode == "cellular"):
            k = 3
        elif(mode == "subcellular"):
            k = 4
        else:
            raise RuntimeError("invalid mode: {}".format(mode))
        m = len(lines[0].split("\t")) - k
        n = len(lines) - 1
        features = np.zeros(shape=(n, m))
        for i in range(1, len(lines)):
            parts = lines[i].rstrip().split("\t")
            for j in range(0, m):
                features[i-1, j] = float(parts[j+k])
    return features


def readDSCForPostId(filename, postId):
    if(not os.path.exists(filename)):
        return None
    with open(filename) as f:
        lines = f.readlines()
        for i in range(1,len(lines)):
            parts = lines[i].rstrip().split(",")
            if(int(parts[0]) == postId):
                return float(parts[1])
    return None