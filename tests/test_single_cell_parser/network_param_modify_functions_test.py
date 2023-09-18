import getting_started
import single_cell_parser as scp
from single_cell_parser.network_param_modify_functions import _has_evoked, _celltype_matches, inactivate_evoked_and_ongoing_activity_by_celltype_and_column

def test_has_evoked():
    param = scp.build_parameters(getting_started.networkParam)
    
    assert(_has_evoked(param, 'L5tt_C2'))
    assert(~_has_evoked(param, 'L1_Beta'))

def test_celltype_matches():
    assert(_celltype_matches('L5tt_C2', ['L5tt'], ['S1']))
    assert(_celltype_matches('L5tt_C2', ['L5tt', 'L4ss'], ['S1']))
    assert(~_celltype_matches('L5tt_C2', ['L5tt', 'L4ss'], ['D2']))
    assert(_celltype_matches('L5tt_C2', ['L5tt', 'L4ss'], ['D2', 'C2']))
    
def test_inactivate_evoked_and_ongoing_activity_by_celltype_and_column():
    param = scp.build_parameters(getting_started.networkParam)
    inactivate_evoked_and_ongoing_activity_by_celltype_and_column(param, ['L5tt'], ['S1'])
    assert('L5tt' not in {k.split('_')[0] for k in list(param.network.keys())})
    param = scp.build_parameters(getting_started.networkParam)
    inactivate_evoked_and_ongoing_activity_by_celltype_and_column(param, ['L4ss'], ['S1'])
    assert('L5tt' in {k.split('_')[0] for k in list(param.network.keys())})
    param = scp.build_parameters(getting_started.networkParam)
    inactivate_evoked_and_ongoing_activity_by_celltype_and_column(param, ['L5tt'], ['C2'])
    assert('L5tt_C2' not in list(param.network.keys()))
    assert('L5tt_D2' in list(param.network.keys()))