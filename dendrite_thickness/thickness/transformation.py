"""
transformation Module

==========
This module contains methods to do transformation on different data am_points.


Capabilities:
----------------------
- Data structure class
-

Limitations:
-----------

"""
from . import IO
import numpy as np


class AffineTransformation:
    def __init__(self):
        self.input_path = None
        self.matrix = None
        self.src_points = None
        self.dst_points = None
        self.points = None
        self.transformed_points = None

    def set_transformation_matrix(self, matrix):
        """
        matrix is a np.array

        """
        self.matrix = matrix

    def set_transformation_matrix_by_landmark_file(self, input_path=None):
        """
        This method computes the transformation based on a landmark file containing 8 am_points.
        The am_points are alternating between first and second coordinate system. Each pair of am_points is
        set on corresponding structures. E.g. in the case of aligning morphologies,
        you would set the landmarks as follows:

        (1) On a characteristic point on the morphology in coordinate system 1
        (2) On the corresponding point on the morphology in coordinate system 2
        (1) On another characteristic point on the morphology in coordinate system 1
        (2) On the corresponding point on the morphology in coordinate system 2
            ... until you have 4 pairs of am_points.
        """
        if input_path is None:
            input_path = self.input_path
            assert input_path
        pair_landmark_points = IO.read_landmark_file(input_path)
        pair_landmark_points = [list(plp) for plp in pair_landmark_points]

        points_system_1 = pair_landmark_points[::2]
        points_system_2 = pair_landmark_points[1::2]

        self.set_transformation_matrix_by_aligned_points(points_system_1, points_system_2)

    def set_transformation_matrix_by_aligned_points(self, src_points, dst_points):
        """
        This function will calculate the affine transformation matrix from
        8 am_points (4 source am_points and 4 destination am_points)

        """

        dst = self.dst_points = dst_points
        src = self.src_points = src_points

        x = np.transpose(np.matrix([src[0], src[1], src[2], src[3]]))
        y = np.transpose(np.matrix([dst[0], dst[1], dst[2], dst[3]]))

        # add ones on the bottom of x and y
        x = np.matrix(np.vstack((x, [1.0, 1.0, 1.0, 1.0])))
        y = np.matrix(np.vstack((y, [1.0, 1.0, 1.0, 1.0])))
        # solve for A2

        matrix = y * x.I
        self.matrix = matrix

    def transform_points(self, points, forwards=True):
        """
        Applies transformation on am_points
        forwards: True: transforms from coordinate system 1 to coordinate system 2
        False: transforms from coordinate system 2 to coordinate system 1

        """

        matrix = self.matrix
        if forwards is False:
            matrix = np.linalg.inv(self.matrix)

        transformed_points = []
        for point4D in points:
            point = point4D[:3]
            m_point = np.matrix(point)
            m_tr_point = m_point.T
            p = matrix * np.matrix(np.vstack((m_tr_point, 1.0)))
            p = np.array(p.T)
            p_listed = p.tolist()[0]
            transformed_points.append(p_listed[0:3] + point4D[3:])

        return transformed_points
    
    def get_amira_transformation_matrix(self):
        return ' '.join(map(str, list(np.array(self.matrix.T).ravel())))


class ConvertPoints:
    """
    This class converts am_points from coordinate_2d to image_coordinate_2d adn vice versa
    inputs.
    x_res: The pixel size in micron for x axis
    y_res: The pixel size in micron for y axis
    z_res: The pixel size in micron for z axis

    """

    def __init__(self, x_res=0.092, y_res=0.092, z_res=1.0):
        self.x_res = x_res
        self.y_res = y_res
        self.z_res = z_res

    def coordinate_2d_to_image_coordinate_2d(self, coordinate_2d):
        """
        Converted am_points from coordinate_2d to image_coordinate_2d

        :param coordinate_2d: TYPE: coordinate_2d
        :return: image_coordinate_2d: TYPE: 2d list of floats, but converted in the unit of the image.

        """
        points = coordinate_2d
        scaling = [1.0 / self.x_res, 1.0 / self.y_res, 1.0 / self.z_res]
        return [_scaling(point, scaling) for point in points]

    def image_coordinate_2d_to_coordinate_2d(self, image_coordinate_2d):
        """
        Converted am_points from image_coordinate_2d to coordinate_2d

        :param image_coordinate_2d: TYPE: 2d list of floats, but converted in th
        :return: coordinate_2d: TYPE: 2d list of floats
        """
        points = image_coordinate_2d
        scaling = [self.x_res, self.y_res, self.z_res]
        return [_scaling(point, scaling) for point in points]

    def thickness_to_micron(self, thicknesses):
        '''coverts thickness (scaled with pixel size) to micron.
        Requires isotropic pixel size in x-y-direction'''
        if self.x_res != self.y_res:
            raise NotImplementedError("Requires isotropic pixel size in x-y-direction!")
        return [t * self.x_res for t in thicknesses]

def _scaling(points, scaling):
    if points is None:
        points = points
        assert points
    out = []
    for lv, pp in enumerate(points):
        try:
            s = scaling[lv]
        except IndexError:
            s = 1
        out.append(pp * s)
    converted_points = out
    return converted_points


def get_distance(p1, p2):
    assert (len(p1) == len(p2))
    return np.sqrt(sum((pp1 - pp2) ** 2 for pp1, pp2 in zip(p1, p2)))
