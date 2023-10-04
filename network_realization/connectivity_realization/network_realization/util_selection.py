def readIds(filename):
    NIDs = []
    with open(filename) as f:
        lines = f.readlines()
        for line in lines:
            line = line.rstrip()
            if(" " in line):
                line = line.split(" ")[0]
            NIDs.append(int(line))
    return NIDs

def readPreIdsMap(filename):
    NIDs = {}
    with open(filename) as f:
        lines = f.readlines()
        for line in lines:
            line = line.rstrip()
            NIDs[int(line.split(" ")[0])] = int(line.split(" ")[1])            
    return NIDs