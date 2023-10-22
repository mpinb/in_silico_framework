"""Initialisation file for the barrel_cortex module

This module should contain everything that's related to the entire barrel cortex.
It includes:
    - average_barrel_field_L45_border.am: barrel cortex geometry, to be rendered in AMIRA
    - barrel_cortex.py: contains functions specific to barrel cortex simulations, such as synaptic strength readout, methods to move morphologies in barrel cortex...

Date: 10/01/2023
"""
import pandas as pd
from functools import partial
import numpy as np
import os
import six
# import single_cell_parser as scp # moved to bottom to resolve import error
from model_data_base import utils


def get_EPSP_measurement():
    EPSP_mean = [0.49, 0.49, 0.35, 0.47, 0.46, 0.44, 0.44, 0.571]
    EPSP_med = [0.35, 0.35, 0.33, 0.33, 0.36, 0.31, 0.31, 0.463]
    EPSP_max = [1.9, 1.9, 1.0, 1.25, 1.5, 1.8, 1.8, 1.18]
    celltypes = ['L2', 'L34', 'L4', 'L5st', 'L5tt', 'L6cc', 'L6ct', 'VPM_C2']
    return pd.DataFrame(
        {
            'EPSP_mean_measured': EPSP_mean,
            'EPSP_med_measured': EPSP_med,
            'EPSP_max_measured': EPSP_max
        },
        index=celltypes)

color_cellTypeColorMap = {'L1': 'cyan', 'L2': 'dodgerblue', 'L34': 'blue', 'L4py': 'palegreen',\
                    'L4sp': 'green', 'L4ss': 'lime', 'L5st': 'yellow', 'L5tt': 'orange',\
                    'L6cc': 'indigo', 'L6ccinv': 'violet', 'L6ct': 'magenta', 'VPM': 'black',\
                    'INH': 'grey', 'EXC': 'red', 'all': 'black', 'PSTH': 'blue'}

color_cellTypeColorMap_L6paper = {'L2': '#119fe4', 'L34': '#0037fe', 'L4py': '#94dc7f',\
                    'L4sp': '#66b56d', 'L4ss': '#66b56d', 'L5st': '#ffec00', 'L5tt': '#d8d8d8',\
                    'L6cc': '#ef9f9e', 'L6ccinv': '#e30210', 'L6ct': '#9933fe', 'VPM': '#1d1d1a'}

color_cellTypeColorMap_L6paper_with_INH = {'L2': '#119fe4', 'L34': '#0037fe', 'L4py': '#94dc7f',\
                    'L4sp': '#66b56d', 'L4ss': '#66b56d', 'L5st': '#ffec00', 'L5tt': 'orange',\
                    'L6cc': '#ef9f9e', 'L6ccinv': '#e30210', 'L6ct': '#9933fe', 'VPM': '#1d1d1a', 'INH': '#d8d8d8'}

color_cellTypeColorMapHotZone = {
    'L23': '#27aae2',
    'L4ss': '#9e1f64',
    'L5tt': '#f7941d',
    'L5st': '#1a75bb',
    'L6CC': '#000000',
    'VPM': '#019444',
    'INT': '#999999'
}

excitatory = [
    'L6cc', 'L2', 'VPM', 'L4py', 'L4ss', 'L4sp', 'L5st', 'L6ct', 'L34',
    'L6ccinv', 'L5tt', 'Generic'
]
inhibitory = [
    'SymLocal1', 'SymLocal2', 'SymLocal3', 'SymLocal4', 'SymLocal5',
    'SymLocal6', 'L45Sym', 'L1', 'L45Peak', 'L56Trans', 'L23Trans',
    'GenericINH', 'INH'
]

#########################################
# transformation tools
#########################################
#p = [[1,2,3], [4,1,2], [1,3,2], [1,1,1], [4,2,5]]


def get_cell_object_from_hoc(hocpath, setUpBiophysics=True):
    import single_cell_parser as scp
    '''returns cell object, which allows accessing points of individual branches'''
    # import singlecell_input_mapper.singlecell_input_mapper.cell
    # ssm = singlecell_input_mapper.singlecell_input_mapper.cell.CellParser(hocpath)
    # ssm.spatialgraph_to_cell()
    # return ssm.cell
    neuron_param = {'filename': hocpath}
    neuron_param = scp.NTParameterSet(neuron_param)
    cell = scp.create_cell(neuron_param, setUpBiophysics=setUpBiophysics)
    return cell


def calculate_point_distance(p1, p2):
    p1, p2 = np.array(p1), np.array(p2)
    return np.sqrt(((p1 - p2)**2).sum())


def get_distance_from_plane(plane_point1, plane_point2, plane_point3,
                            outside_point):
    p1p2 = np.array(plane_point2) - np.array(plane_point1)
    p1p3 = np.array(plane_point3) - np.array(plane_point1)
    n = np.cross(p1p2, p1p3)
    assert len(n) == 3
    if n[2] < 0:
        n = n * -1
    n = n * 1 / (np.sqrt((n**2).sum()))
    c = (n * plane_point1).sum()
    return n, c, (n * outside_point).sum() - c


def norm(x):
    x = np.array(x)
    return x / np.sqrt((x**2).sum())


@utils.cache
def read_barrelfield():
    mapping_label_id = {'A1': 13, 'A2': 14, 'A3': 15, 'A4': 16,\
                        'B1': 18, 'B2': 19, 'B3': 20, 'B4': 21,\
                        'C1': 23, 'C2': 24, 'C3': 25, 'C4': 26, 'C5': 27, 'C6': 28,\
                        'D1': 30, 'D2': 31, 'D3': 32, 'D4': 33, 'D5': 34, 'D6': 35,\
                        'E1': 37, 'E2': 38, 'E3': 39, 'E4': 40, 'E5': 41, 'E6': 42, \
                        'Alpha': 44, 'Beta': 45, 'Gamma': 46, 'Delta': 47}
    mapping_id_position = [
        44, 13, 14, 15, 16, 45, 18, 19, 20, 21, 46, 23, 24, 25, 26, 47, 30, 31,
        32, 33, 37, 38, 39, 40
    ]
    mapping_id_position = {x: lv for lv, x in enumerate(mapping_id_position)}
    n_edge_points = 37
    edge_points = six.StringIO()
    average_barrel_field_path = os.path.join(
        os.path.dirname(__file__), 'average_barrel_field_L45_border.am')
    with open(average_barrel_field_path) as f:
        skip = True
        for l in f.readlines():
            if not skip:
                edge_points.write(l)
                if not l.strip():
                    break
            if l.strip() == '@6':
                skip = False
    edge_points.seek(0)
    edge_points = pd.read_csv(edge_points, names=['raw'], sep='\t')
    edge_points = edge_points.apply(
        lambda x: pd.Series(x.raw.split(' '))[:3].astype(float), axis=1)
    #edge_points = edge_points.dropna()

    invert_dict = lambda my_map: dict((v, k) for k, v in six.iteritems(my_map))

    def get_edge_points_by_label(label):
        id_ = mapping_label_id[label]
        position = mapping_id_position[id_] * 37
        return edge_points

    label_column = []
    for lv in sorted(invert_dict(mapping_id_position).keys()):
        id_ = invert_dict(mapping_id_position)[lv]
        label = invert_dict(mapping_label_id)[id_]
        label_column.extend([label] * n_edge_points)

    edge_points['label'] = label_column
    barrel_center_points = edge_points.groupby('label').apply(np.mean)

    def fun(x):
        x = x.drop('label', axis=1).iloc[[0, 10, 20, 30]].values.tolist()
        n, c, dist = get_distance_from_plane(*x)
        assert dist < 0.01
        return pd.Series(n)

    z_axis = edge_points.groupby('label').apply(fun)

    return edge_points, barrel_center_points, z_axis


def convertible_to_float(x):
    try:
        float(x)
        return True
    except:
        return False


def construct_pt3add(values):
    values = tuple(values)
    return "{pt3dadd(%.6f, %.6f, %.6f, %.6f)}\n" % values


def extract_pt3add(line, selfcheck=False):
    line_dummy = line.replace('(', ' ').replace(')', ' ').replace(',',
                                                                  ' ').split()
    values = [float(s) for s in line_dummy if convertible_to_float(s)]
    if selfcheck:
        if not line.replace(" ", "") == construct_pt3add(values).replace(
                " ", ""):
            raise ValueError("Can't reproduce input %s, result would be %s" %
                             (line, construct_pt3add(values)))
    return values


def transform_point(p, x, y, z, coordinate_system=None):
    x_, y_, z_ = get_xyz(coordinate_system)
    return np.array(p) + x * x_ + y * y_ + z * z_


def get_soma_centroid(hocpath):
    from model_data_base.utils import silence_stdout
    source_soma_points = get_cell_object_from_hoc(hocpath).soma.pts
    soma_centroid = np.array(source_soma_points).mean(axis=0)
    return soma_centroid


def move_hoc_xyz(hocpath, x, y, z, outpath=None, coordinate_system='D2'):
    '''moves hoc morphology in xyz directions in the coordinate system of the specified barrel.
    Cave: The coordinate system might be different from Roberts definition of local coordinate systems.
    It is generated as follows:
    - z is the local z axis of the column 
    - x has the same orientation as in the global coordinate system, but is tilted in 
    its z component to be orthogonal on the locaal z axis.
    - y is orthogonal to both, roughly pointing in the y direction of the global coordinate system
    '''
    out = []
    with open(hocpath, 'r') as f:
        for line in f.readlines():
            if 'pt3dadd' in line:
                values = extract_pt3add(line)
                v = transform_point(values[:3], x, y, z, coordinate_system)
                line = construct_pt3add(list(v) + [values[3]])
            out.append(line)
    if outpath is None:
        return out
    else:
        if not os.path.exists(os.path.dirname(outpath)):
            os.makedirs(os.path.dirname(outpath))
        with open(outpath, 'w') as f:
            f.writelines(out)


def move_hoc_absolute(hocpath, x, y, z, outpath=None):
    '''moves hoc morphology such that soma centroid is at absolute position x,y,z.
    The coordinates must be in the global coordinate system, i.e. D2
    '''
    out = []
    # transform to relative coordinates
    x, y, z = np.array([x, y, z]) - get_soma_centroid(hocpath)
    move_hoc_xyz(hocpath, x, y, z, outpath=outpath, coordinate_system='D2')


def move_hoc_to_hoc(
    hoc_in,
    hoc_reference,
    outpath=None,
):
    centroid_in = get_soma_centroid(hoc_in)
    centroid_reference = get_soma_centroid(hoc_reference)
    x, y, z = centroid_reference - centroid_in
    move_hoc_xyz(hoc_in, x, y, z, outpath=outpath, coordinate_system='D2')


@utils.cache
def get_xyz(column):
    '''returns base vectors were 
    - z is the local z axis of the column 
    - x has the same orientation as in the global coordinate system, but is tilted in 
    its z component to be orthogonal on the locaal z axis.
    - y is orthogonal to both, roughly pointing in the y direction of the 
    global coordinate system'''
    edge_points, barrel_center_points, z_axis = read_barrelfield()
    n = z_axis.loc[column].values
    x_ = norm([1, 0, -n[0] / n[2]])
    z_ = n
    y_ = norm(np.cross(z_, x_))
    return x_, y_, z_


#np.testing.assert_almost_equal(get_xyz('D2')[0], [1,0,0])
#np.testing.assert_almost_equal(get_xyz('D2')[1], [0,1,0])
#np.testing.assert_almost_equal(get_xyz('D2')[2], [0,0,1])


def get_distance_below_L45_barrel_surface(p, barrel='C2'):
    '''distance below L45 surface of individual barrel'''
    edge_points, barrel_center_points, z_axis = read_barrelfield()
    three_points = edge_points[edge_points.label == barrel].drop(
        'label', axis=1).iloc[[0, 10, 20]].values.tolist()
    return get_distance_from_plane(*(three_points + [p]))[-1]


def get_distance_below_L45_surface(p):
    '''surface is interpolated from barrel center points'''
    edge_points, barrel_center_points, z_axis = read_barrelfield()
    three_nearest_points = barrel_center_points.apply(
        lambda x: calculate_point_distance(x.values, p),
        axis=1).sort_values().index[:3].values
    three_nearest_points = barrel_center_points.loc[
        three_nearest_points].values.tolist()
    return get_distance_from_plane(*(three_nearest_points + [p]))[-1]


def get_z_coordinate_necessary_to_put_point_in_specified_depth(
    p,
    depth,
    coordinate_system_z_move='C2',
    measure_fun=partial(get_distance_below_L45_barrel_surface, barrel='C2')):
    d0 = measure_fun(transform_point(p, 0, 0, 0, coordinate_system_z_move))
    d1 = measure_fun(transform_point(p, 0, 0, 1, coordinate_system_z_move))
    current_depth = measure_fun(p)
    return (depth - current_depth) / (d1 - d0)


def correct_hoc_depth(hoc_in,
                      hoc_reference_or_depth,
                      coordinate_system_z_move='C2',
                      measure_fun=partial(get_distance_below_L45_barrel_surface,
                                          barrel='C2'),
                      outpath=None):
    ''' Variables:
    reference_depth_or_hoc: depth in which to put morphology, either specified through float or 
        a path to a hoc morphology from which the soma centroid position will be extracted and used as depth
    coordinate_system_z_move: which z axis to choose to move the morphology. 
        Must be one of the barrels ('C1', 'Alpha', ...)
    measure_fun: function that receives a point and returns a depth. Typical choices:
        partial(get_distance_below_L45_barrel_surface, barrel = 'C2')
        get_distance_below_L45_surface
    '''
    if isinstance(hoc_reference_or_depth, str):
        centroid_reference = get_soma_centroid(hoc_reference_or_depth)
        depth = measure_fun(centroid_reference)
    else:
        depth = hoc_reference_or_depth
    centroid = get_soma_centroid(hoc_in)
    z = get_z_coordinate_necessary_to_put_point_in_specified_depth(
        centroid,
        depth,
        coordinate_system_z_move=coordinate_system_z_move,
        measure_fun=measure_fun)
    move_hoc_xyz(hoc_in,
                 0,
                 0,
                 z,
                 outpath=outpath,
                 coordinate_system=coordinate_system_z_move)


def get_3x3_C2_soma_centroids():
    return {
        'B1border': [
            -201.46530018181818, 470.56739184090895, -386.4753397045454
        ],
        'B2border': [
            -117.62110088636364, 507.9633913863634, -393.07710399999996
        ],
        'B3border': [
            -30.016312340909096, 467.9283842500001, -392.9739968863636
        ],
        'C1border': [
            -241.86630115909094, 391.47840263636357, -378.67699979545455
        ],
        'C2center': [
            -119.4026019318182, 389.5003752045455, -384.52578529545457
        ],
        'C3border': [3.061196454545454, 388.32438034090904, -388.4764383863637],
        'D1border': [
            -203.98930222727276, 304.5671781818183, -374.7777994090909
        ],
        'D2border': [-121.2830036590909, 265.8940825, -374.7777383863637],
        'D3border': [
            -37.46331304545455, 300.5537810227273, -378.67699979545455
        ]
    }


def create_3x3(hocpath_C2, outdir):
    for name, centroid in six.iteritems(get_3x3_C2_soma_centroids()):
        x, y, z = centroid
        outpath = os.path.join(outdir, name + '.hoc')
        move_hoc_absolute(hocpath_C2, x, y, z, outpath=outpath)
        correct_hoc_depth(hoc_in=outpath,
                          hoc_reference_or_depth=hocpath_C2,
                          coordinate_system_z_move='C2',
                          measure_fun=partial(
                              get_distance_below_L45_barrel_surface,
                              barrel='C2'),
                          outpath=outpath)


#import getting_started
#hocpath = scp.build_parameters(getting_started.neuronParam).neuron.filename
#with utils.mkdtemp() as d:
#    create_3x3(hocpath, d)
#    print os.listdir(d)


def create_9x9(hocpath_C2, outdir):
    centroids = get_3x3_C2_soma_centroids()
    name = 'C2center'
    x, y, z = centroids[name]
    outpath = os.path.join(outdir, 'x_0_y_0.hoc')
    move_hoc_absolute(hocpath_C2, x, y, z, outpath=outpath)
    correct_hoc_depth(hoc_in=outpath,
                      hoc_reference_or_depth=hocpath_C2,
                      coordinate_system_z_move='C2',
                      measure_fun=partial(get_distance_below_L45_barrel_surface,
                                          barrel='C2'),
                      outpath=outpath)
    for x in range(-200, 250, 50):
        for y in range(-200, 250, 50):
            outpath2 = os.path.join(outdir, 'x_{}_y_{}.hoc'.format(x, y))
            move_hoc_xyz(outpath,
                         x,
                         y,
                         0,
                         outpath=outpath2,
                         coordinate_system='C2')


#import getting_started
#hocpath = scp.build_parameters(getting_started.neuronParam).neuron.filename
#with utils.mkdtemp() as d:
#    create_9x9(hocpath, d)
#    print os.listdir(d)


def create_SuC(hocpath_C2, outdir):
    centroids = get_3x3_C2_soma_centroids()
    name = 'C2center'
    x, y, z = centroids[name]
    outpath = os.path.join(outdir, 'x_0_y_0.hoc')
    move_hoc_absolute(hocpath_C2, x, y, z, outpath=outpath)
    correct_hoc_depth(hoc_in=outpath,
                      hoc_reference_or_depth=hocpath_C2,
                      coordinate_system_z_move='C2',
                      measure_fun=partial(get_distance_below_L45_barrel_surface,
                                          barrel='C2'),
                      outpath=outpath)
    for x in range(-600, 800, 100):
        for y in range(-500, 700, 100):
            outpath2 = os.path.join(outdir, 'x_{}_y_{}.hoc'.format(x, y))
            move_hoc_xyz(outpath,
                         x,
                         y,
                         0,
                         outpath=outpath2,
                         coordinate_system='C2')
            correct_hoc_depth(outpath2,
                              outpath,
                              coordinate_system_z_move='C2',
                              measure_fun=get_distance_below_L45_surface,
                              outpath=outpath2)


#import getting_started
#hocpath = scp.build_parameters(getting_started.neuronParam).neuron.filename
#with utils.mkdtemp() as d:
#    create_SuC(hocpath, d)
#    print os.listdir(d)

# import Interface as I