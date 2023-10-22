import numpy as np
from .context import *


def test_apply_release_probability():
    prob = 0.3
    arr = [[[1, 2, 3], [2, 3, 4]], [[3, 4, 5]], []]
    reference_len = len(list(utils.flatten(arr)))
    _arr = [len(list(utils.flatten(PostCell._apply_release_probability_and_merge(arr, prob)))) \
            / float(reference_len)
     for lv in range(10000)]
    assert np.mean(_arr) < prob + 0.01
    assert np.mean(_arr) > prob - 0.01


def test_get_SA_array():
    array = [[1, 2, 3, 2, 3, 4], [3, 4, 5], []]
    PostCell._get_SA_array(array, 5)
    expected = np.array([[0, 1, 2, 2, 1], [0, 0, 0, 1, 2], [0, 0, 0, 0, 0]])
    np.testing.assert_array_equal(PostCell._get_SA_array(array, 5), expected)
