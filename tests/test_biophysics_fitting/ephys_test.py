import numpy as np
from . import decorators
from . import context

from biophysics_fitting.ephys import find_crossing, find_crossing_old


def test_find_crossing_and_find_crossing_old_are_equivalent():
    for lv in range(100):
        v = np.random.rand(1000)
        result1 = find_crossing(v, 0.9)
        result2 = find_crossing_old(v, 0.9)
        np.testing.assert_array_equal(result1, result2)


def test_find_crossing():
    l = [1, 1, 2, 3, 3, 3, 2, 1, 3, 1, 1, 1, 1, 1, 3, 1, 1, 1]
    assert find_crossing(l, 2) == [[3, 8, 14], [6, 9, 15]]
    assert find_crossing(l, 2.5) == [[3, 8, 14], [6, 9, 15]]
    # assert find_crossing(l + [3], 2.5) == [[], []]
