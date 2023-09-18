from single_cell_analyzer.membrane_potential_analysis import simple_spike_detection

def test_spike_detection_respects_threshold():
    assert(simple_spike_detection([0,1,2,3,4,5,6], [-5,-4,-3,-2,-1,0,1]) == [5])
    assert(simple_spike_detection([0,1,2,3,4,5,6], [-5,-4,-3,-2,-1,0,1], threshold=-2) == [3])