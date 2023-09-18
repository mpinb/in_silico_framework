from barrel_cortex import *
from .context import barrel_center_points

def test_pt3add():
    teststr = "{pt3dadd(-191.183289, 445.022980, -402.017792, 0.450000)}\n"
    assert(teststr == construct_pt3add(extract_pt3add(teststr)))

def test_transform_point():
    assert((transform_point(transform_point([0,0,0], 1, 0, 0, 'C2'), -1, 0, 0, 'C2') == [0,0,0]).all())
    
def test_move_hoc_xyz():
    import getting_started
    import single_cell_parser as scp
    hocpath = scp.build_parameters(getting_started.neuronParam).neuron.filename
    with utils.mkdtemp() as d:
        centroid =  get_soma_centroid(hocpath) 
        outpath1 = os.path.join(d, 'hoc.hoc') 
        outpath2 = os.path.join(d, 'hoc2.hoc') 
        move_hoc_xyz(hocpath, 1,2,3, outpath1, 'D2')
        move_hoc_xyz(outpath1, -1,-2,-3, outpath2, 'D2')
        centroid2 = get_soma_centroid(outpath2) 
        np.testing.assert_almost_equal(centroid, centroid2)
        move_hoc_xyz(outpath1, -1,-2,-3, outpath2, 'C2')
        centroid2 = get_soma_centroid(outpath2)
        assert((centroid != centroid2).all())

def test_move_hoc_absolute():
    import getting_started
    import single_cell_parser as scp
    hocpath = scp.build_parameters(getting_started.neuronParam).neuron.filename
    with utils.mkdtemp() as d:
        outpath = os.path.join(d, 'hoc.hoc') 
        move_hoc_absolute(hocpath, 0,0,0, outpath = outpath)
        np.testing.assert_array_almost_equal(get_soma_centroid(outpath), [0,0,0])

def test_move_hoc_to_hoc():
    import getting_started
    import single_cell_parser as scp  
    hocpath = scp.build_parameters(getting_started.neuronParam).neuron.filename
    with utils.mkdtemp() as d:
        outpath1 = os.path.join(d, 'hoc.hoc') 
        move_hoc_xyz(hocpath, 1,2,3, outpath1, 'C2')
        outpath2 = os.path.join(d, 'hoc2.hoc') 
        move_hoc_to_hoc(hoc_in = hocpath, hoc_reference = outpath1, outpath = outpath2)
        centroid1 =  get_soma_centroid(outpath1) 
        centroid2 =  get_soma_centroid(outpath2) 
        np.testing.assert_almost_equal(centroid1, centroid2)

def test_get_distance_below_L45_barrel_surface():
    np.testing.assert_almost_equal(get_distance_below_L45_barrel_surface(barrel_center_points.loc['C2'],
                                                                         barrel = 'C2'), 
                                   0, 
                                   decimal = 3)
    np.testing.assert_almost_equal(get_distance_below_L45_barrel_surface(barrel_center_points.loc['D2'],
                                                                         barrel = 'D2'), 
                                   0, 
                                   decimal = 3)
    
def test_get_distance_below_L45_surface():
    np.testing.assert_almost_equal(get_distance_below_L45_surface(barrel_center_points.loc['C2']), 0)
    np.testing.assert_almost_equal(get_distance_below_L45_surface(barrel_center_points.loc['D2']), 0)

def test_correct_hoc_depth():
    import getting_started
    import single_cell_parser as scp
    hocpath = scp.build_parameters(getting_started.neuronParam).neuron.filename
    with utils.mkdtemp() as d:
        outpath = os.path.join(d, 'hoc.hoc') 
        measure_fun = partial(get_distance_below_L45_barrel_surface, barrel = 'C2')
        correct_hoc_depth(hoc_in = hocpath, hoc_reference_or_depth = 0, coordinate_system_z_move = 'C2', 
                          measure_fun = measure_fun, 
                          outpath = outpath)
        centroid = get_soma_centroid(outpath)
        depth = measure_fun(centroid)
        np.testing.assert_almost_equal(depth, 0, decimal = 5)

        outpath2 = os.path.join(d, 'hoc2.hoc') 
        correct_hoc_depth(hoc_in = hocpath, hoc_reference_or_depth = 0, coordinate_system_z_move = 'D2', 
                          measure_fun = measure_fun, 
                          outpath = outpath2)
        centroid2 = get_soma_centroid(outpath2)
        depth2 = measure_fun(centroid2)
        np.testing.assert_almost_equal(depth, 0, decimal = 5)
        assert((centroid != centroid2).all())