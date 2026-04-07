from .context import HOC_FN, SWC_FN, NEUP_FN
import single_cell_parser as scp
import os
import re
from data_base.utils import silence_stdout
import neuron
from numpy.testing import assert_almost_equal
from single_cell_parser.io.morphology import convert_hoc_to_swc, convert_swc_to_hoc
import filecmp

h = neuron.h

def setup_current_injection_experiment(
        morph_fn=None
        ):
    cell_param = scp.build_parameters(NEUP_FN)
    # load scaled hoc morphology
    cell_param.neuron.filename = morph_fn
    with silence_stdout:
        cell = scp.create_cell(cell_param.neuron)

    iclamp = h.IClamp(0.5, sec=cell.soma)
    iclamp.delay = 150  # give the cell time to reach steady state
    iclamp.dur = 5  # 5ms rectangular pulse
    iclamp.amp = 1.9  # 1.9 ?? todo ampere

    scp.init_neuron_run(cell_param.sim, vardt=True)  # run the simulation

    return cell


def test_convert_swc_to_hoc(tmpdir):
    tmp_swc = str(tmpdir / "swc1.swc")
    tmp_hoc = str(tmpdir / "hoc1.hoc")

    convert_swc_to_hoc(swc_fn=SWC_FN, of=tmp_hoc)
    convert_hoc_to_swc(hoc_fn=tmp_hoc, of=tmp_swc)
    assert filecmp.cmp(f1=SWC_FN, f2=tmp_swc)

    
def test_convert_hoc_to_swc(tmpdir):
    # TODO: labels get remapped to internal repr. Find better way to test equality
    tmp_swc = tmpdir / "swc2.swc"
    tmp_hoc = tmpdir / "hoc2.hoc"

    convert_hoc_to_swc(HOC_FN, tmp_swc)
    convert_swc_to_hoc(
        tmp_swc, 
        tmp_hoc,
    )

    def ignore_soma_children(line):
        """Children of soma may connect at different x after conversion"""
        pattern = r"connect.*Soma\(\d\.\d+\)"
        return not re.search(pattern, line)
    with open(HOC_FN, 'r') as f1, open(tmp_hoc, 'r') as f2:
        f1 = filter(ignore_soma_children, f1)
        f2 = filter(ignore_soma_children, f2)
        assert all(x == y for x, y in zip(f1, f2))
    

def test_swc_hoc_give_same_results():
    # TODO: results deviate?
    cell1 = setup_current_injection_experiment(morph_fn=HOC_FN)
    cell2 = setup_current_injection_experiment(morph_fn=SWC_FN)

    t1, t2 = [t for t in cell1.tVec], [t for t in cell2.tVec]
    v1, v2 = [v for v in cell1.soma.recVList[0]], [v for v in cell2.soma.recVList[0]]

    assert t1 == t2
    assert_almost_equal(v1, v2)