# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.

"""
Thickness Module

==========
This module contains methods to do extract thicknesses from image.


Capabilities:
----------------------
-
-

Limitations:
-----------


"""
import os
import sys

import numpy as np
import warnings
import SimpleITK as sitk
from . import transformation as tr
from .utils import get_size_of_object
from . import utils as u
import itertools
import logging

logger = logging.getLogger("ISF").getChild(__name__)


class ThicknessExtractor:

    def __init__(
            self,
            points,
            image_file=None,
            xy_resolution=0.092,
            z_resolution=0.5,
            ray_length_front_to_back_in_micron=20,
            number_of_rays=36,
            threshold_percentage=0.5,
            max_seed_correction_radius_in_micron=10,
            _3d=False,
            image_stack=None,
            slice_name=None):
        """ This is the main method for extracting Thickness
        - Inputs:
            1. am_points: must be in the type transformation.Data.coordinate_2d, so they are a list of
            2d values in micrometer
            2. Image is the path to tif file with a pixel size of xy_resolution.
            3. xy_resolution: pixelSize in micrometers as acquired by the microscope in one optical section.
            4. z_resolution: z distance in micrometers between optical sections
            5. ray_length_front_to_back_in_micron: maximum distance from the seed point considered in micrometer.

        """

        # slice_name is a handy object that can help distinguishes between multiple instances of this class.
        self.slice_name = slice_name
        self.original_points = points
        self.convert_points = tr.ConvertPoints(xy_resolution, xy_resolution,
                                               z_resolution)
        points_in_image_coordinates_2d = self.convert_points.coordinate_2d_to_image_coordinate_2d(
            self.original_points)
        self.points = points_in_image_coordinates_2d  # image_coordinate_2d, TYPE: 2d list of floats,
        # but converted in the unit of the image.
        self.seed_corrected_points = []
        # TYPE: Must be transformation.Data.image_coordinate_2d

        self.image_stack = image_stack
        # We don't set the whole image_stack (eg. : by self._set_image() ) here since the memory usage will
        # be much less if we read the corresponding image on demand of each point.
        # image_stack is a dictionary with keys as z_coordinate indicator, and values
        # of each key is the path of image correspondent to that special z_coordinate. eg:
        # { "000": "path to the image with z000.tif"
        #   "001": "path to the image with z001.tif"
        #   ...
        #   "102": "path to the image with z101.tif"
        # }
        self._3D = _3d
        self.current_z_coordinate = None
        # Set the _3D flag to True, the class will expect to use the full stack images and will not
        # detect overlap, since it does not needed anymore.

        self.xy_resolution = xy_resolution
        self.z_resolution = z_resolution
        # ray_length_front_to_back_in_micron, is the size of total ray in micron.
        self.ray_length_front_to_back_in_micron = ray_length_front_to_back_in_micron
        self.number_of_rays = number_of_rays
        self._ray_length_per_direction_in_micron = ray_length_front_to_back_in_micron / 2.0
        # __ray_length_per_direction_of_image_coordinates: by dividing _ray_length_per_direction_in_micron with the
        # xy_resolution we go to the image coordinate system.
        # So the numbers in this coordinate are indication of pixels.
        self._ray_length_per_direction_of_image_coordinates = self._ray_length_per_direction_in_micron / xy_resolution
        self.threshold_percentage = threshold_percentage
        self._max_seed_correction_radius_in_image_coordinates = max_seed_correction_radius_in_micron / xy_resolution
        self._max_seed_correction_radius_in_image_coordinates_in_pixel = \
            int(self._max_seed_correction_radius_in_image_coordinates)
        self.padded_image = None
        self.contour_list = []
        self.all_overlaps = []
        self.all_data = {}

        self.image_file = image_file
        if image_file is not None:
            self._set_image(image_file)

        # the thicknesses_list is what you will finally searching for from this class. It contains the min_thickness of
        # each point which will be fill from all_data after all of the processing. The index of each thickness is the
        # same as the index of point or in am_points list. So one can find the corresponding thickness of each point by
        # looking at its index in thickness_list all over the program. Be careful that the thicknesses in thickness_list
        # is converted back to the coordinate_3d system. But the corresponding min_thickness
        # in all_data[point_index]["min_thickness"] is in image_coordinate system
        self.thickness_list = []
        if self.image_file is None and self._3D is False:
            raise RuntimeError("You need to provide an image_file path")

        self.get_all_data_by_points()

    def get_all_data_by_points(self):
        """
        This is the main method of the class.
        To extract the thicknesses of am_points from the image, after initiating the class, this method need to be called.

        """

        # sort am_points for the 3D case to load image plane after image plane
        sort_indices = np.argsort([x[2] for x in self.points])
        sorted_points = [self.points[x] for x in sort_indices]

        all_data = {}
        for idx, point in enumerate(sorted_points):
            if self._3D:
                self._set_image_file_by_point(point)
            data = self.get_all_data_by_point(point)
            all_data[idx] = data
            all_data[idx]["overlaps"] = []
            logger.info(
                str(idx) + " am_points from " + str(len(sorted_points)) +
                " from slice " + self.slice_name + " are completed.")
            sys.stdout.write("\033[F")

        import six
        all_data = {sort_indices[k]: v for k, v in six.iteritems(all_data)}
        self.all_data = all_data
        logger.info("size of object in MB all_data: " +
                 str(get_size_of_object(all_data) / (1024. * 1024.)))

        # if self._3D is False:
        # self.all_overlaps = self.update_all_data_with_overlaps()

        self._get_thicknesses_from_all_data()

    def get_all_data_by_point(self, point):
        """
        Computes coordinates of rays and intensity profiles for one point.

        :param point: The TYPE Must be transformation.coordinate_2d.
        so the point is in Micrometer unit.
        :return: A dictionary of am_points as keys and all_data as the value.
        all_data itself is a dictionary of:
        1. back_profile, 2. front_profile, 3. thicknesses_list,
        4. min_thickness, 5. back_contour_index, 6. front_contour_index,
        7. contour_list, 8. rays_intensity_profile, 9. rays_indices, 10. selected_profile_index

        """

        all_data = {"converted_point_by_image_coordinate": point}
        if self._max_seed_correction_radius_in_image_coordinates:
            point = self._correct_seed(point)
        all_data["seed_corrected_point"] = point
        self.seed_corrected_points.append(point)
        thicknesses_list = []
        min_thickness = np.Inf
        contour_list = []
        rays_intensity_profile = []
        rays_indices = []

        for i in range(self.number_of_rays):
            phi = i * (np.pi / self.number_of_rays)

            front_ray_indices = self.get_ray_points_indices(point,
                                                            phi,
                                                            front=True)
            back_ray_indices = self.get_ray_points_indices(point,
                                                           phi,
                                                           front=False)

            ray_indices = _construct_ray_from_half_rays(front_ray_indices,
                                                        back_ray_indices, point)
            rays_indices.append(ray_indices)

            ray_intensity_profile = self.get_intensity_profile_from_ray_indices(
                ray_indices)
            rays_intensity_profile.append(ray_intensity_profile)

        # all_data["rays_indices"] = rays_indices
        # all_data["rays_intensity_profile"] = rays_intensity_profile

        for i, ray_indices in enumerate(rays_indices):

            ray_length = len(ray_indices)
            half_ray_length = int((ray_length - 1) / 2)

            back_contour_index = self.get_contour_index(
                point, ray_indices[0:half_ray_length + 1][::-1])
            front_contour_index = self.get_contour_index(
                point, ray_indices[half_ray_length:ray_length])
            all_data["back_contour_index"] = back_contour_index
            all_data["front_contour_index"] = front_contour_index
            if back_contour_index is None or front_contour_index is None:
                thickness = 0.
            else:
                assert (len(back_contour_index) == 2)
                assert (len(front_contour_index) == 2)
                thickness = tr.get_distance(back_contour_index,
                                            front_contour_index)
            contour_list.append([back_contour_index, front_contour_index])
            thicknesses_list.append(thickness)

            if thickness < min_thickness:
                min_thickness = thickness
                all_data["min_thickness"] = min_thickness
                all_data["selected_ray_index"] = i

        all_data["contour_list"] = contour_list
        all_data["thicknesses_list"] = thicknesses_list
        return all_data

    def get_intensity_profile_from_ray_indices(self, ray_indices):
        image = self.image
        profile_values = []
        profile_indices_length = len(ray_indices)
        for i in range(profile_indices_length):
            try:
                pixel = [(int(x)) for x in ray_indices[i]]
                intensity_value = image.GetPixel(pixel)
            except RuntimeError as error:
                logger.warn(error)
                intensity_value = 0
            profile_values.append(intensity_value)
        return profile_values

    def get_contour_index(self, point, ray_indices):

        image = self.image
        point_indices = [int(point[0]), int(point[1])]
        try:
            point_value = image.GetPixel(point_indices)
        except RuntimeError as error:
            logger.warn("Point outside the image! Assuming diameter 0")
            return None

        # pointHalfValue = point_value/2.0
        point_threshold_value = point_value * self.threshold_percentage
        profile_indices_length = len(ray_indices)
        contour_indices = None
        for i in range(profile_indices_length):

            # this may not fail: point indices are in image
            # all further am_points have been queried with
            # image.GetPixel(ray_indices[i+1])
            pixel_1_value = image.GetPixel(ray_indices[i])

            # this fails, if we have reached the end of the ray
            try:
                _index = ray_indices[i + 1]
            except IndexError:
                logger.warn(
                    "End of ray reached! Center point intensity: {}".format(
                        point_value))
                return ray_indices[i]

            # this fails, if the ray goes out of the image
            try:
                pixel_2_value = image.GetPixel(_index)
            except IndexError as error:
                logger.warn("Ray goes out of image! Assuming diameter 0")

            if pixel_1_value >= point_threshold_value >= pixel_2_value:
                contour_indices = ray_indices[i]
                break

        assert contour_indices is not None
        return contour_indices

    def get_ray_points_indices(self, point, phi, front):
        """
        This method will get a point in image coordinate system, and will return the ray indices from that point
         by the value of phi.
        :param point:
        :param phi:
        :param front:
        :return: ray indices. They are in pixel in image coordinate system.
        """
        image = self.image
        ray_length = self._ray_length_per_direction_of_image_coordinates

        ray_points_indices = []

        image_width = image.GetWidth()
        image_height = image.GetHeight()

        x_i = point[0]
        y_i = point[1]

        x_f = x_i
        y_f = y_i

        for index in range(int(ray_length)):

            if front:
                x_f = x_f + 1
            else:
                x_f = x_f - 1

            x_f = x_f - x_i
            y_f = y_f - y_i

            x_new = int(y_f * np.sin(phi) + x_f * np.cos(phi))
            y_new = int(y_f * np.cos(phi) - x_f * np.sin(phi))

            x_new = x_new + x_i
            y_new = y_new + y_i

            x_f = x_f + x_i
            y_f = y_f + y_i

            if x_new <= 1 or y_new <= 1 or x_new >= image_width or y_new >= image_height:
                break
            else:
                ray_points_indices.append([int(x_new), int(y_new)])

        return ray_points_indices

    def _correct_seed(self, point):
        """
        Given an input point of format [x, y, intensity_value], this method corrects the point by 
        finding the nearest point with the highest intensity value. How "near" is defined by the
        self._max_seed_correction_radius_in_image_coordinates_in_pixel parameter.

        Args:
            point (array): The image coordinates of the point to be corrected. Format: [x, y, intensity_value]

        Returns:
            corrected_point: The corrected point. Format: [new_x, new_y, original_intensity_value]
        """
        # point = [int(point[0]), int(point[1]), point[2]]
        radius = self._max_seed_correction_radius_in_image_coordinates_in_pixel
        point_in_padded_image = point[0] + radius, point[1] + radius
        cropped_image = _crop_image(self.padded_image,
                                    point_in_padded_image,
                                    radius,
                                    circle=True)
        indices_of_max_value = np.argwhere(
            cropped_image == np.amax(cropped_image)).ravel()
        corrected_point = [
            indices_of_max_value[0] + point[0] - radius,
            indices_of_max_value[1] + point[1] - radius, point[2]
        ]

        intensity_value = self.image.GetPixel([int(point[0]), int(point[1])])
        intensity_value2 = self.image.GetPixel(
            [int(corrected_point[0]),
             int(corrected_point[1])])
        assert intensity_value2 >= intensity_value
        logger.info('original_point: {} / {} corrected_point: {} / {}'.format(
            point, intensity_value, corrected_point, intensity_value2))
        return corrected_point

    def update_all_data_with_overlaps(self):
        points = self.seed_corrected_points
        overlaps = []
        cubes = [
            u.get_neighbours_of_point(point, points, width=2)
            for point in points
        ]
        for cube in cubes:
            if len(cube) == 0:
                continue
            overlaps.append(([
                self.find_overlap(p1, p2)
                for p1 in cube
                for p2 in cube
                if p1 != p2
            ]))
        return overlaps

    def find_overlap(self, point_1, point_2):
        data_1 = self._filter_all_data_by_point(point_1)
        keys_1 = sorted(data_1.keys())
        contours_1 = data_1[keys_1[0]]["contour_list"]

        data_2 = self._filter_all_data_by_point(point_2)
        keys_2 = sorted(data_2.keys())
        contours_2 = data_2[keys_2[0]]["contour_list"]

        if _check_overlap(contours_1, contours_2):
            self.all_data[keys_1[0]]["overlaps"].append([point_1, point_2])
            self.all_data[keys_2[0]]["overlaps"].append([point_2, point_1])

            # if u.compare_points(point1, point2) >= 10E-14:
            return [point_1, point_2]

    def _filter_all_data_by_point(self, point):
        return dict([
            x for x in list(self.all_data.items())
            if x[1]["seed_corrected_point"] == point
        ])

    def _set_image_file_by_point(self, point):
        z_coordinate_key = int(point[2])
        if z_coordinate_key != self.current_z_coordinate:
            self._set_image(self.image_stack[z_coordinate_key])
        self.current_z_coordinate = z_coordinate_key

    def _set_image(self, input_path):
        logger.info('setting image path to {}'.format(input_path))
        self.image = _read_image(input_path)
        self.padded_image = _pad_image(
            self.image,
            self._max_seed_correction_radius_in_image_coordinates_in_pixel)

    def _get_thicknesses_from_all_data(self):
        thickness_list = [
            self.all_data[idx]["min_thickness"]
            for idx in range(len(self.points))
        ]
        self.thickness_list = self.convert_points.thickness_to_micron(
            thickness_list)

    def __del__(self):
        del self.image_stack
        del self.padded_image
        del self.points
        del self.convert_points
        del self.contour_list
        del self.seed_corrected_points


def _check_overlap(contour1, contour2):
    polygon_lines1 = _create_polygon_lines_by_contours(contour1)
    polygon_lines2 = _create_polygon_lines_by_contours(contour2)
    for line1 in polygon_lines1:
        for line2 in polygon_lines2:
            ints = _get_intersection(line1, line2)
            if line1[0][0] <= ints[0] <= line1[1][0] and line1[0][1] <= ints[
                    1] <= line1[1][1]:
                return True
    return False


def _slope(p1, p2):
    logger.info(p1)
    if p1[0] - p2[0] == 0:
        return np.inf
    return (p1[1] - p2[1]) / (p1[0] - p2[0])


def _intercept(m, p2):
    return -m * p2[0] + p2[1]


def _create_polygon_lines_by_contours(contour):
    polygon_lines = []
    edge_pairs = [[p1, p2]
                  for i, p1 in enumerate(contour)
                  for p2 in contour[i:]
                  if p1 != p2 and p1 != []]
    for edge_pair in edge_pairs:
        p1 = edge_pair[0]
        p2 = edge_pair[1]
        m = _slope(p1, p2)
        b = _intercept(m, p2)
        line = [p1, p2, m, b]
        polygon_lines.append(line)
    return polygon_lines


def _get_intersection(line1, line2):
    if line1[2] - line2[2] == 0:
        return [np.inf, np.inf]
    x = (line2[3] - line1[3]) / (line1[2] - line2[2])
    y = line1[2] * x + line1[3]
    return [x, y]


def _circle_filter(x, y, r):
    """Check if a point is within a circle of radius :paramref: r and center (0,0)

    Args:
        x (int/float)
        y (int/float)
        r (int/float)

    Returns:
        int: 1 if the point is within the circle, 0 otherwise
    """
    if x**2 + y**2 <= r**2:
        return 1
    else:
        return 0


def _pad_image(image, radius):
    image_array = sitk.GetArrayFromImage(image)
    image_array = np.transpose(image_array)
    return np.pad(image_array, radius, 'constant', constant_values=0)


def _crop_image(image_array, center, radius, circle=False):
    """Given an image as a 2D array, this method crops it around :paramref:center.
    The crop is either a square of size 2x:paramref:radius by 2x:paramref:radius and center :paramref:center,
    or, in case :paramref:circle equals True, a circle with radius :paramref:radius.

    Args:
        image_array (array): The 2D image array
        center (array): 1x2 array of xy coordinates. Coordinates should be the index of pixels. 
        radius (int): size of the crop in both directions. Total size will be 
        circle (bool, optional): _description_. Defaults to False.

    Returns:
        np.array: 2D array of the cropped image  # TODO 2 by N or 3 by N?
    """
    c1, c2 = int(center[0]), int(center[1])
    # assert (c1 - radius >= 0)
    # assert (c2 - radius >= 0)

    return_ = image_array[c1 - radius:c1 + radius + 1,
                          c2 - radius:c2 + radius + 1]
    # return_ = b_pad[c1:c1 + 2 * radius + 1, c2:c2 + 2 * radius + 1]

    if circle:
        return_ = [[
            value * _circle_filter(row_lv - radius, col_lv - radius, radius)
            for col_lv, value in enumerate(row)
        ]
                   for row_lv, row in enumerate(return_)]
        return_ = np.array(return_)
    return return_


def _construct_ray_from_half_rays(front_ray_indices, back_ray_indices, point):
    """puts together two half rays and center point and returns full ray.

    front_ray_indices: List of lists of two integers reflecting the x-y-pixel position for the front_ray
    back_ray_indices: as above, for the back_ray
    point: center point of the ray (list of two integers)

    """
    center_point_index = [int(point[0]), int(point[1])]
    ray = list(reversed(back_ray_indices)) + [center_point_index
                                             ] + front_ray_indices
    return ray


def _read_image(image_file):
    """Reading image file """
    image_file_reader = sitk.ImageFileReader()
    image_file_reader.SetFileName(image_file)
    image = image_file_reader.Execute()
    return image
