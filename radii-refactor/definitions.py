import os
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT_DIR, 'configuration.conf')

"""Definitions of Data structures:
        1. coordinate_2d, TYPE: 2d list of floats
        2. image_coordinate_2d, TYPE: 2d list of floats, in a relative unit such that 1 reflects the pixel size:
        3. coordinate, TYPE: 3d list of floats
        4. coordinate_with_radius, TYPE: 4d list of floats
        5. pixel_coordinate, TYPE: 2d list of integers
        6. indices: 2d pixel position in an image, list of 2 integers.
        7. src_points,
        8. ds_points,
"""