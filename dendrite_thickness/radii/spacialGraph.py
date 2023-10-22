import math


def getSpatialGraphPoints(spatial_graph):
    """
    #input: path of the data.
    #output: pints in an array
    """

    with open(spatial_graph, 'r') as csb:
        edge_ids = []
        edge_num_points = []
        edge_point_coords = []

        looking_for_axon_id = False
        looking_for_dend_id = False
        looking_for_soma_id = False
        looking_for_num_edge_points = False
        looking_for_edge_labels = False
        looking_for_edge_coords = False

        axon_id = 0
        dend_id = 0
        soma_id = 0
        edge_num_points_id = 0
        edge_ids_id = 0
        edge_points_id = 0

        lines = csb.readlines()

        # for each manual landmark
        for lv, line in enumerate(lines):

            if line.rfind("EDGE { int NumEdgePoints } @") > -1:
                edge_num_points_id = int(
                    line[line.rfind("EDGE { int NumEdgePoints } @") +
                         len("EDGE { int NumEdgePoints } @"):])
                #print 'edge_num_points_id', edge_num_points_id

            if line.rfind("EDGE { int EdgeLabels } @") > -1:
                edge_ids_id = int(line[line.rfind("EDGE { int EdgeLabels } @") +
                                       len("EDGE { int EdgeLabels } @"):])
                #print 'edge_ids_id', edge_ids_id

            if line.rfind("POINT { float[3] EdgePointCoordinates } @") > -1:
                edge_points_id = int(
                    line[line.rfind("POINT { float[3] EdgePointCoordinates } @"
                                   ) +
                         len("POINT { float[3] EdgePointCoordinates } @"):])
                #print 'edge_points_id', edge_points_id

            if line.find("@{}".format(edge_num_points_id)) == 0:
                looking_for_num_edge_points = True
                #print "found {}".format(edge_num_points_id)
                continue
            if looking_for_num_edge_points:
                if (line.rfind("@") == 0 or line.isspace()):
                    looking_for_num_edge_points = False
                    continue
                else:
                    edge_num_points.append(int(line))

            if line.find("@{}".format(edge_ids_id)) == 0:
                looking_for_edge_labels = True
                #print "found {}".format(edge_ids_id)
                continue
            if looking_for_edge_labels:
                if (line.rfind("@") == 0 or line.isspace()):
                    looking_for_edge_labels = False
                    continue
                else:
                    edge_ids.append(int(line))

            if line.find("@{}".format(edge_points_id)) == 0:
                looking_for_edge_coords = True
                #print lv
                #print "found {}".format(edge_points_id)
                continue
            if looking_for_edge_coords:
                if (line.rfind("@") == 0 or line.isspace()):
                    looking_for_edge_coords = False
                    continue
                else:
                    edge_point_coords.append(list(map(float, line.split())))
                    #edge_point_coords.append( float(line.split()))

    return edge_point_coords


def write_spacial_graph_with_thickness(inpath, outpath, radii):
    '''by arco'''
    with open(inpath) as f:
        data = f.readlines()

    for lv, line in enumerate(data):
        if line.rfind("POINT { float[3] EdgePointCoordinates } @") > -1:
            edge_points_id = int(
                line[line.rfind("POINT { float[3] EdgePointCoordinates } @") +
                     len("POINT { float[3] EdgePointCoordinates } @"):])
            break

    thickness_id = edge_points_id + 1

    data = data[:lv + 1] + [
        'POINT { float thickness } @' + str(thickness_id) + '\n'
    ] + data[lv + 1:]

    with open(outpath, 'w') as f:
        f.writelines(data)
        f.write('\n')
        f.write('@' + str(thickness_id) + '\n')
        for r in radii:
            if math.isnan(r):
                f.write(str(0.0) + '\n')
            else:
                f.write(str(r) + '\n')
