import numpy as np
from data_base.analyze._add_nparray_aligned import *


class TestAddNumpyArrayAligned:

    def setup_class(self):
        self.a = np.array([[1, 2], [3, 4]])
        self.b = np.array([[1, 2, 3], [3, 4, 5]])
        self.c = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

    def test_max_size(self):
        '''tests the max_size function, which expects np.ndarray
        objects as argument. This function should return 
        the maximum size in each direction.'''
        a = self.a
        b = self.b
        assert [2, 3] == max_array_dimensions(a, b)
        assert [2, 3] == max_array_dimensions(a, a, b)
        assert [2, 3] == max_array_dimensions(a, b, b)
        assert [2, 3] == max_array_dimensions(b, a)
        assert [2, 2] == max_array_dimensions(a)

    def test_add_samesize(self):
        a = self.a
        b = self.b
        np.testing.assert_equal(add_aligned(a, a), a * 2)

    def test_add_different_size(self):
        a = self.a
        b = self.b
        c = self.c
        d = np.array([])
        np.testing.assert_equal(add_aligned(a, c),
                                np.array([[2, 4, 3], [7, 9, 6], [7, 8, 9]]))
        np.testing.assert_equal(add_aligned(a, b),
                                np.array([[2, 4, 3], [6, 8, 5]]))
        np.testing.assert_equal(add_aligned(a, b, d),
                                np.array([[2, 4, 3], [6, 8, 5]]))
        add_aligned(d, d, d)
