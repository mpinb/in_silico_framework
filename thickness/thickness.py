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


Tests
-----

- The test functions are inside the test.py. One can also use them as example of how to use the functions.

"""
from __future__ import division

import sys
import numpy as np
import warnings
import SimpleITK as sitk
import transformation as tr
from utils import get_size_of_object
import utils as u
import time


class ThicknessExtractor:
    def __init__(self, points, image_file=None, xy_resolution=0.092, z_resolution=0.5,
                 ray_length_front_to_back_in_micron=20,
                 number_of_rays=36, threshold_percentage=0.5, max_seed_correction_radius_in_micron=10, _3d=False,
                 image_stack=None, slice_name=None):
        """ This is the main method for extracting Thickness
        - Inputs:
            1. am_points: must be in the type transformation.Data.coordinate_2d, so they are a list of
            2d values in micrometer
            2. Image is the path to tif file with a pixel size of xy_resolution.
            3. xy_resolution: pixelSize in micrometers as acquired by the microscope in one optical section.
            eg -> 0.092 micron/pixel
            4. z_resolution: z distance in micrometers between optical sections
            5. ray_length_front_to_back_in_micron: maximum distance from the seed point considered in micrometer.

        """

        # slice_name is a handy object that can help distinguishes between multiple instances of this class.
        self.slice_name = slice_name
        self.original_points = points
        self.convert_points = tr.ConvertPoints(xy_resolution, xy_resolution, z_resolution)
        points_in_image_coordinates_2d = self.convert_points.coordinate_2d_to_image_coordinate_2d(self.original_points)
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
        To extract the thicknesses of am_points from the image, after initiating the class,
        this method need to be called.
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
            all_data[idx]["overlaps_point_id"] = []
        #            print str(idx) + " am_points from " + str(
        #                len(sorted_points)) + " from slice " + self.slice_name + " are completed."
        #            sys.stdout.write("\033[F")

        all_data = {sort_indices[k]: v for k, v in all_data.iteritems()}
        self.all_data = all_data
        #        print "size of object in MB all_data: " + str(get_size_of_object(all_data) / (1024. * 1024.))

        if self._3D is False:
            self.all_overlaps = self.update_all_data_with_overlaps()
        self._get_thicknesses_from_all_data()
        self._tidy_up()

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
        all_data["seed_corrected_point_in_image_coordinate"] = point
        self.seed_corrected_points.append(point)
        thicknesses_list = []
        min_thickness = np.Inf
        contour_list = []
        rays_intensity_profile = []
        rays_indices = []

        for i in range(self.number_of_rays):
            phi = i * (np.pi / self.number_of_rays)

            front_ray_indices = self.get_ray_points_indices(point, phi, front=True)
            back_ray_indices = self.get_ray_points_indices(point, phi, front=False)

            ray_indices = _construct_ray_from_half_rays(front_ray_indices, back_ray_indices, point)
            rays_indices.append(ray_indices)

            ray_intensity_profile = self.get_intensity_profile_from_ray_indices(ray_indices)
            rays_intensity_profile.append(ray_intensity_profile)

        # all_data["rays_indices"] = rays_indices
        # all_data["rays_intensity_profile"] = rays_intensity_profile

        for i, ray_indices in enumerate(rays_indices):

            ray_length = len(ray_indices)
            half_ray_length = (ray_length - 1) // 2

            back_contour_index = self.get_contour_index(point, ray_indices[0:half_ray_length + 1][::-1])
            front_contour_index = self.get_contour_index(point, ray_indices[half_ray_length:ray_length])
            all_data["back_contour_index"] = back_contour_index
            all_data["front_contour_index"] = front_contour_index
            if back_contour_index is None or front_contour_index is None:
                thickness = 0.
            else:
                assert (len(back_contour_index) == 2)
                assert (len(front_contour_index) == 2)
                thickness = tr.get_distance(back_contour_index, front_contour_index)
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
                pixel = map(lambda x: (int(x)), ray_indices[i])
                intensity_value = image.GetPixel(pixel)
            except RuntimeError as error:
                warnings.warn(error)
                intensity_value = 0
            profile_values.append(intensity_value)
        return profile_values

    def get_contour_index(self, point, ray_indices):

        image = self.image
        point_indices = [int(point[0]), int(point[1])]
        try:
            point_value = image.GetPixel(point_indices)
        except RuntimeError as error:
            warnings.warn("Point outside the image! Assuming diameter 0")
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
                warnings.warn("End of ray reached! Center point intensity: {}".format(point_value))
                return ray_indices[i]

            # this fails, if the ray goes out of the image
            try:
                pixel_2_value = image.GetPixel(_index)
            except IndexError as error:
                warnings.warn("Ray goes out of image! Assuming diameter 0")

            if pixel_1_value >= point_threshold_value >= pixel_2_value:
                contour_indices = ray_indices[i]
                break

        assert (contour_indices is not None)
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
        # point = [int(point[0]), int(point[1]), point[2]]
        radius = self._max_seed_correction_radius_in_image_coordinates_in_pixel
        point_in_padded_image = point[0] + radius, point[1] + radius
        cropped_image = _crop_image(self.padded_image, point_in_padded_image, radius, circle=True)
        indices_of_max_value = np.argwhere(cropped_image == np.amax(cropped_image)).ravel()
        corrected_point = [indices_of_max_value[0] + point[0] - radius,
                           indices_of_max_value[1] + point[1] - radius,
                           point[2]]

        intensity_value = self.image.GetPixel([int(point[0]), int(point[1])])
        intensity_value2 = self.image.GetPixel([int(corrected_point[0]), int(corrected_point[1])])
        assert (intensity_value2 >= intensity_value)
        # print 'original_point: {} / {} corrected_point: {} / {}'.format(point, intensity_value,
        #                                                                 corrected_point, intensity_value2)
        return corrected_point

    def _tidy_up(self):
        del self.image
        del self.padded_image
        del self.points
        del self.convert_points
        del self.contour_list

    def update_all_data_with_overlaps(self):
        seed_corrected_points = self.seed_corrected_points
        points = self.points  # original points in image 2d coordinate
        overlaps = []
        all_overlaps = []
        visited_pairs = []
        # start = time.time()
        volumes = [[p_idx, u.get_neighbours_of_point(p, points, width=108, dimensions=[0, 1], indices=True)] for
                   p_idx, p in enumerate(points)]

        # volumes = [[p, u.get_neighbours_of_point(p, seed_corrected_points, width=108, dimensions=[0, 1])]
        # for p in seed_corrected_points]
        # end = time.time()
        # print "time for finding near points:" + str(end - start)
        # print (len(points))
        # print(len(volumes))
        end = 0.0
        for i, volume in enumerate(volumes):
            start = time.time()
            if not i % 300:
                print "volume number:", i, "from", len(volumes)
                print "number of points to check:", len(volume[1])
                print "time:", end - start
            # start = time.time()
            # pairs = [[p1, p2] for i, p1 in enumerate(volume) for p2 in volume[i + 1:]
            #          if p1 != p2 and [p1, p2] not in visited_pairs]
            #   center_point = volume[0]
            #   ng_points = volume[1]
            center_point_idx = volume[0]
            ng_points_idx = volume[1]
            # pairs = [[center_point, ng_point] for ng_point in ng_points if center_point != ng_point]
            index_pairs = [[center_point_idx, ng_point_idx] for ng_point_idx in ng_points_idx]
            # end = time.time()
            # print "time for getting pairs:" + str(end - start)
            for pair in index_pairs:
                overlap = self.look_for_possible_overlap(pair[0], pair[1])
                if len(overlap) != 0:
                    overlaps.append(overlap)
                # Check if I can remove the below line
                # Answer: No Since [p1,p2] is same as [p2,p1] but the above cond. does not check for the inverse.
                # visited_pairs.append(pair)
                # visited_pairs.append(pair[::-1])

            all_overlaps.append(overlaps)
            end = time.time()
        return all_overlaps

    def look_for_possible_overlap(self, idx_point_1, idx_point_2):

        # start = time.time()
        #        data_point_1 = self._filter_all_data_by_point(point_1)
        #        keys_point_1 = sorted(data_point_1.keys())
        #        original_point_1 = self.original_points[keys_point_1[0]]
        #        contours_list_point_1 = data_point_1[keys_point_1[0]]["contour_list"]
        # point_1_in_image_coordinate = data_point_1[keys_point_1[0]]["converted_point_by_image_coordinate"]
        #        min_thickness_point_1 = data_point_1[keys_point_1[0]]["min_thickness"]
        p_1 = self.points[idx_point_1]
        p_2 = self.points[idx_point_2]

        # Points in coordinates 2d
        original_p1 = self.original_points[idx_point_1]
        original_p2 = self.original_points[idx_point_2]

        seed_corrected_p1 = self.seed_corrected_points[idx_point_1]
        seed_corrected_p2 = self.seed_corrected_points[idx_point_2]
        data_p1 = self._filter_all_data_by_index(idx_point_1)
        data_p2 = self._filter_all_data_by_index(idx_point_2)
        contour_list_p1 = data_p1["contour_list"]
        contour_list_p2 = data_p2["contour_list"]
        min_thickness_p1 = data_p1["min_thickness"]
        min_thickness_p2 = data_p2["min_thickness"]

        overlaps_p1 = data_p1["overlaps"]
        overlaps_p2 = data_p2["overlaps"]

        # data_point_2 = self._filter_all_data_by_point(point_2)
        # keys_point_2 = sorted(data_point_2.keys())
        # original_point_2 = self.original_points[keys_point_2[0]]
        # contours_list_point_2 = data_point_2[keys_point_2[0]]["contour_list"]
        # min_thickness_point_2 = data_point_2[keys_point_2[0]]["min_thickness"]

        # end = time.time()
        # print "time for filtering data by point:" + str(end - start)
        # point_2_in_image_coordinate = data_point_2[keys_point_2[0]]["converted_point_by_image_coordinate"]

        # print "seed_corrected_point", point_1
        # print "original_point", original_point_1
        # print "point_1 in image coordinate", point_1_in_image_coordinate
        # print "original_point from translation",\
        #     self.convert_points.image_coordinate_2d_to_coordinate_2d([point_1_in_image_coordinate])
        # start = time.time()
        check_bool = _check_contours_intersect(contour_list_p1, contour_list_p2)

        # if seed_corrected_p1 == seed_corrected_p2 or original_p1 == original_p2:
        #     check_bool = True
        # else:
        #     check_bool = _check_circle_overlap([seed_corrected_p1, min_thickness_p1 / 2.0],
        #                                               [seed_corrected_p2, min_thickness_p2 / 2.0])
        # if not check_bool and check_circle_bool:
        #     print "contours overlap:", check_bool
        #     print "circular overlap:", check_circle_bool
        # end = time.time()
        # print "time check for overlap:" + str(end - start)

        if check_bool:
            # start = time.time()
            # for l in self.all_data[keys_point_1[0]]["overlaps"], self.all_data[keys_point_2[0]]["overlaps"]:
            #     for p in original_point_1, original_point_2:
            #         if not (p in l):
            #             l.append(p)
            if original_p1 not in overlaps_p1:
                overlaps_p1.append(original_p1)
            if original_p2 not in overlaps_p1:
                overlaps_p1.append(original_p2)

            if original_p1 not in overlaps_p2:
                overlaps_p2.append(original_p1)
            if original_p2 not in overlaps_p2:
                overlaps_p2.append(original_p2)

            # for r in self.all_data[keys_point_1[0]]["overlaps_point_id"], self.all_data[keys_point_2[0]]["overlaps_point_id"]:
            #     for p in keys_point_1[0], keys_point_2[0]:
            #         if not (p in r):
            #             r.append(p)

            # end = time.time()
            # print "time check for adding overlaps:" + str(end - start)
            # self.all_data[keys_point_1[0]]["overlaps"].append(original_point_1)
            # self.all_data[keys_point_2[0]]["overlaps"].append([original_point_2, original_point_1])

            # self.all_data[keys_point_1[0]]["overlaps_point_id"].append([keys_point_1[0], keys_point_2[0]])
            # self.all_data[keys_point_2[0]]["overlaps_point_id"].append([keys_point_2[0], keys_point_1[0]])

            # if u.compare_points(point1, point2) >= 10E-14:
            return [p_1, p_2]
        else:
            return []

    def _filter_all_data_by_point(self, point):
        # using pythonic syntax -> dictionarry comprehension
        return dict(filter(lambda x:
                           x[1]["seed_corrected_point_in_image_coordinate"] == point, self.all_data.iteritems()))

    def _filter_all_data_by_index(self, idx_point):
        return self.all_data[idx_point]

    def _set_image_file_by_point(self, point):
        z_coordinate_key = int(point[2])
        if z_coordinate_key != self.current_z_coordinate:
            self._set_image(self.image_stack[z_coordinate_key])
        self.current_z_coordinate = z_coordinate_key

    def _set_image(self, input_path):
        # print 'setting image path to {}'.format(input_path)
        self.image = _read_image(input_path)
        self.padded_image = _pad_image(self.image, self._max_seed_correction_radius_in_image_coordinates_in_pixel)

    def _get_thicknesses_from_all_data(self):
        thickness_list = [self.all_data[idx]["min_thickness"] for idx in range(len(self.points))]
        self.thickness_list = self.convert_points.thickness_to_micron(thickness_list)


def _check_z_difference(point1, point2, delta_z=0.1):
    if abs(point1[2] - point2[2]) <= delta_z:
        return True
    else:
        return False


def _circle_filter(x, y, r):
    if x ** 2 + y ** 2 <= r ** 2:
        return 1
    else:
        return 0


def _pad_image(image, radius):
    image_array = sitk.GetArrayFromImage(image)
    image_array = np.transpose(image_array)
    return np.pad(image_array, radius, 'constant', constant_values=0)


def _crop_image(image_array, center, radius, circle=False):
    c1, c2 = int(center[0]), int(center[1])
    assert (c1 - radius >= 0)
    assert (c2 - radius >= 0)

    return_ = image_array[c1 - radius:c1 + radius + 1, c2 - radius:c2 + radius + 1]
    # return_ = b_pad[c1:c1 + 2 * radius + 1, c2:c2 + 2 * radius + 1]

    if circle:
        return_ = [[value * _circle_filter(row_lv - radius, col_lv - radius, radius)
                    for col_lv, value in enumerate(row)]
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
    ray = list(reversed(back_ray_indices)) + [center_point_index] + front_ray_indices
    return ray


def _read_image(image_file):
    """Reading image file """
    image_file_reader = sitk.ImageFileReader()
    image_file_reader.SetFileName(image_file)
    image = image_file_reader.Execute()
    return image


def _check_circle_overlap(c1, c2):
    p1 = c1[0]
    r1 = c1[1]

    p2 = c2[0]
    r2 = c2[1]

    dist = tr.get_distance(p1, p2)
    if dist <= r1 + r2:
        return True
    return False


def _check_point_in_line(point, line):
    """
    check if a special position (point) in the line is bw to other points (p1, p2) in the line or not.

    :param point: 2D point,[x,y], this point must be in the line already.
    :param line: [p1,p2,m,b], p1,p2: points in the line, m is the slop and b is the intercept. p1, p2 are the
    two corners on the polygon (only two of them which make the this side of the polygon).
    :return: True if the input point is in this line bw two corners.
    """

    p1 = line[0]
    p2 = line[1]
    assert (p1 != p2)

    if p1[0] <= p2[0]:
        if p1[1] <= p2[1]:
            if p1[0] <= point[0] <= p2[0] and p1[1] <= point[1] <= p2[1]:
                return True
        else:
            if p1[0] <= point[0] <= p2[0] and p2[1] <= point[1] <= p1[1]:
                return True

    if p2[0] <= p1[0]:
        if p1[1] <= p2[1]:
            if p2[0] <= point[0] <= p1[0] and p1[1] <= point[1] <= p2[1]:
                return True
        else:
            if p2[0] <= point[0] <= p1[0] and p2[1] <= point[1] <= p1[1]:
                return True

    #    origin = [0.0,0.0]
    #    r1 = tr.get_distance(origin, p1)
    #    r2 = tr.get_distance(origin, p2)
    #    r = tr.get_distance(origin, point)
    #    print r1,r2,r
    #    if r1 <= r <= r2 or r2 <= r <= r1:
    #        return True'
    return False


def _slope(p1, p2):
    assert (p1 != p2)
    #    if p1 == p2:
    #        raise ValueError("Slope is undefined for identical points!")
    if p1[0] - p2[0] == 0:
        return np.inf
    return (p1[1] - p2[1]) / (p1[0] - p2[0])


def test_slope():
    res = _slope([0, 1], [0, 2])
    assert (res == np.inf)
    #    try:
    #        res = _slope([0,1],[0,1])
    #    except ValueError:
    #        pass
    #    else:
    #        raise RuntimeError("This should have caused a ZeroDivisionError!")
    res = _slope([0, 0], [2, 2])
    assert (res == 1)


test_slope()


def _intercept(m, p):
    return -m * p[0] + p[1]


def test_intercept():
    m = 0
    point = [0, 0]
    assert (0 == _intercept(m, point))

    m = np.inf
    point = [1, 1]
    assert (-np.inf == _intercept(m, point))

    m = np.inf
    point = [-1, -1]
    assert (np.inf == _intercept(m, point))


# test_intercept()


def _create_polygon_lines_by_contours(contour):
    polygon_lines = []
    edge_pairs = _find_edges_of_polygon_from_contours(contour)
    for edge_pair in edge_pairs:
        polygon_lines.append(_create_line(edge_pair[0], edge_pair[1]))
    return polygon_lines


def _create_line(p1, p2):
    m = _slope(p1, p2)
    b = _intercept(m, p2)
    line = [p1, p2, m, b]
    return line


def _find_edges_of_polygon_from_contours(contour):
    pts = [p[0] for p in contour] + [p[1] for p in contour]
    pairs = zip(pts, pts[1:] + [pts[0]])
    return [list(p) for p in pairs]  # convert tuple to list


def test_find_edges_of_polygon_from_contours():
    p1, p2, p3, p4 = [0, 1], [0, -1], [1, 0], [-1, 0]
    pts = [[p1, p2], [p3, p4]]
    edge_pairs = _find_edges_of_polygon_from_contours(pts)
    edge_pairs_expected = [[p1, p3], [p3, p2], [p2, p4], [p4, p1]]
    assert (edge_pairs == edge_pairs_expected)


# test_find_edges_of_polygon_from_contours()


def _get_intersection(line1, line2):
    if line1[2] == 0.0 and line2[2] == 0.0:
        return "parallel, horizontal"

    if line1[2] ** 2 == np.inf and line2[2] ** 2 == np.inf:
        return "parallel, vertical"

    if line1[2] == line2[2]:
        return "parallel"

    if line1[2] ** 2 == 0.0 and line2[2] ** 2 == np.inf:
        return [line2[0][0], line1[0][1]]

    if line1[2] ** 2 == np.inf and line2[2] ** 2 == 0.0:
        return [line1[0][0], line2[0][1]]

    if line1[2] ** 2 == np.inf and (line2[2] ** 2 != np.inf and line2[2] ** 2 != 0.0):
        x = line1[0][0]
        y = line2[2] * x + line2[3]
        return [x, y]

    if line2[2] ** 2 == np.inf and (line1[2] ** 2 != np.inf and line1[2] ** 2 != 0.0):
        x = line2[0][0]
        y = line1[2] * x + line1[3]
        return [x, y]

    if line1[2] ** 2 == 0.0 and line2[2] != np.inf and line2[2] != 0.0:
        y = line1[0][1]
        x = (y - line2[3]) / line2[2]
        return [x, y]

    if line2[2] ** 2 == 0.0 and line1[2] != np.inf and line1[2] != 0.0:
        y = line2[0][1]
        x = (y - line1[3]) / line1[2]
        return [x, y]

    x = (line2[3] - line1[3]) / (line1[2] - line2[2])
    y = line1[2] * x + line1[3]
    return [x, y]


def _test_get_intersection():
    # y = m1*x + b1
    # y = m2*x + b2
    # Solution:
    # x = (b2 -b1)/(m1 - m2)
    # y = m1(b2 -b1)/(m1 -m2) + b1 OR y = m1(b2 -b1)/(m1 -m2) + b1

    # When the two lines are parallel m1 = m2
    # line1: y = 1*x + 0
    # line2: y = 1*x + 1
    line1 = _create_line([0.0, 0.0], [1.0, 1.0])
    line2 = _create_line([0.0, 1.0], [1.0, 2.0])
    assert (_get_intersection(line1, line2) == "parallel")

    # When the two lines are horizontal lines, m1 = m2 = 0
    # line1: y = 0*x + 1
    # line2: y = 0*x + 2
    line1 = _create_line([0.0, 1.0], [1.0, 1.0])
    line2 = _create_line([0.0, 2.0], [-1.0, 2.0])
    assert (_get_intersection(line1, line2) == "parallel, horizontal")

    # When the two lines are vertical lines, m1 = m2 = infinity
    # line1: x = - 1
    # line2: x = + 2
    line1 = _create_line([-1.0, -2.0], [-1.0, 11.0])
    line2 = _create_line([2.0, 1.0], [2.0, 3.0])
    assert (_get_intersection(line1, line2) == "parallel, vertical")

    # When one line is vertical, and the other is horizontal:
    # line1: x = - 1
    # line2: y = + 2
    line1 = _create_line([-1.0, 1.0], [-1.0, 2.0])
    line2 = _create_line([1.0, 2.0], [3.0, 2.0])
    assert (_get_intersection(line1, line2) == [-1.0, 2.0])

    # When one line is vertical, and the other is horizontal:
    # line1: y =  3
    # line2: x = - 2
    line1 = _create_line([-1.0, 3.0], [1.0, 3.0])
    line2 = _create_line([-2.0, 2.0], [-2.0, -8.0])
    assert (_get_intersection(line1, line2) == [-2.0, 3.0])

    # When one of the lines is horizontal and the other is not vertical nor horizontal:
    # line1: y = -1
    # line2: y = 2*x - 1
    line1 = _create_line([-1.0, -1.0], [2.0, -1.0])
    line2 = _create_line([0.0, -1.0], [1.0, 1.0])
    assert (_get_intersection(line1, line2) == [0.0, -1.0])

    # When one of the lines is vertical and the other is not vertical nor horizontal:
    # line1: x = 2
    # line2: y = 2*x - 1
    line1 = _create_line([2.0, -1.0], [2.0, 1.0])
    line2 = _create_line([0.0, -1.0], [1.0, 1.0])
    assert (_get_intersection(line1, line2) == [2.0, 3.0])

    # line1: y = 1*x + 1
    # line2: x = 3
    line1 = _create_line([1.0, 2.0], [2.0, 3.0])
    line2 = _create_line([3., -1.0], [3.0, 1.0])
    assert (_get_intersection(line1, line2) == [3.0, 4.0])

    # when lines are not vertical nor horizontal:
    # line1: y = 2*x + 1
    # line2: y = -3*x +1
    line1 = _create_line([0.0, 1.0], [1.0, 3.0])
    line2 = _create_line([0.0, 1.0], [1.0, -2.0])
    assert (_get_intersection(line1, line2) == [0.0, 1.0])


# _test_get_intersection()


def _drop_duplications_from_contour(contours):
    cs_dropped = [ctr for id_ctr, ctr in enumerate(contours)
                  if ctr[0] != ctr[1] and
                  ctr[0] not in [c2 for ctr2 in contours[:id_ctr] for c2 in ctr2] and
                  ctr[1] not in [c2 for ctr2 in contours[:id_ctr] for c2 in ctr2]]
    return cs_dropped


def _test_drop_duplications_from_contour():
    c1 = [[[2609, 3341], [2621, 3341]],
          [[2609, 3343], [2618, 3339]],
          [[2607, 3352], [2614, 3339]],
          [[2613, 3344], [2613, 3340]],
          [[2614, 3343], [2613, 3340]],
          [[2615, 3342], [2611, 3340]]]

    c1_dropped = [[[2609, 3341], [2621, 3341]],
                  [[2609, 3343], [2618, 3339]],
                  [[2607, 3352], [2614, 3339]],
                  [[2613, 3344], [2613, 3340]],
                  [[2615, 3342], [2611, 3340]]]
    assert _drop_duplications_from_contour(c1) == c1_dropped

    c2 = [[[2609, 3341], [2621, 3341]],
          [[2609, 3343], [2618, 3339]],
          [[2607, 3352], [2614, 3339]],
          [[2607, 3352], [2614, 3339]],
          [[2613, 3344], [2613, 3340]],
          [[2614, 3343], [2613, 3340]],
          [[2615, 3342], [2607, 3352]]]

    c2_dropped = [[[2609, 3341], [2621, 3341]],
                  [[2609, 3343], [2618, 3339]],
                  [[2607, 3352], [2614, 3339]],
                  [[2613, 3344], [2613, 3340]]]

    assert _drop_duplications_from_contour(c2) == c2_dropped


# _test_drop_duplications_from_contour()


def _check_polygon_inside(line, polygon):
    a_ints_line = [_get_intersection(line, p_line)
                   for p_line in polygon
                   if "parallel" not in str(_get_intersection(line, p_line))
                   and _check_point_in_line(_get_intersection(line, p_line), p_line)]

    # This is for a very rare case when one line is touching exactly the intersection of another two lines,
    # In this case if the polygon is outside the other it will only have these two intersections, but if
    # one polygon is inside the other one then for sure it has more than two intersections so the below
    # condition will not full filled nad
    if len(a_ints_line) < 2:
        return False
    if len(a_ints_line) == 2 and a_ints_line[0] == a_ints_line[1]:
        return False

    a_p = [[ints_p1, ints_p2] for ints_p1 in a_ints_line for ints_p2 in a_ints_line]
    a_dists = [tr.get_distance(pp[0], pp[1]) for pp in a_p]
    idx_max = a_dists.index(max(a_dists))
    two_points = a_p[idx_max]
    # 2nd: Take this another review for the necessity of the below. Noted on 21 July 2020
    #    if two_points[0] == two_points[1]:
    #        return False
    new_ints_line = _create_line(two_points[0], two_points[1])
    if _check_point_in_line(line[0], new_ints_line) and _check_point_in_line(line[1], new_ints_line):
        return True
    return False


def _check_contours_intersect(contour_1, contour_2):
    if contour_1 == contour_2:
        return True

    contour_1 = _drop_duplications_from_contour(contour_1)
    contour_2 = _drop_duplications_from_contour(contour_2)

    polygon_lines_1 = _create_polygon_lines_by_contours(contour_1)
    polygon_lines_2 = _create_polygon_lines_by_contours(contour_2)

    for line1 in polygon_lines_1:
        for line2 in polygon_lines_2:
            ints = _get_intersection(line1, line2)
            if "parallel" in str(ints):
                continue
            # check if intersect is in edges of both polygons
            if _check_point_in_line(ints, line1):
                if _check_point_in_line(ints, line2):
                    return True
    count_ints_p1 = []
    count_ints_p2 = []
    for id_l1, line1 in enumerate(polygon_lines_1):
        for id_l2, line2 in enumerate(polygon_lines_2):
            ints = _get_intersection(line1, line2)
            if "parallel" in str(ints):
                continue
            if _check_point_in_line(ints, line1):
                if _check_polygon_inside(line2, polygon_lines_1):
                    count_ints_p1.append(True)
            elif _check_point_in_line(ints, line2):
                if _check_polygon_inside(line1, polygon_lines_2):
                    count_ints_p2.append(True)

        if len(count_ints_p1) >= len(2 * polygon_lines_2) or len(count_ints_p2) >= len(2 * polygon_lines_1):
            return True
    return False


def recenter_contours(contours):
    cs_f = [p for contour in contours for p in contour]
    mean_xy = np.mean(np.array(cs_f), axis=0)
    cs_centered = np.around((np.array(cs_f) - mean_xy), decimals=1).tolist()
    cs_centered_list = [[cs_centered[idx], cs_centered[idx + 1]] for idx in range(0, len(cs_centered), 2)]
    return cs_centered_list


def get_overlap_contour_list(point, table):
    idx = table[['x_slice', 'y_slice', 'z_slice']].values.tolist().index(point)
    return table.iloc[idx]["contour_list_0.5"]


def plot_polygons(polygons, plt):
    colors = ["#0000FF", "#00FF00"]
    f, ax = plt.subplots(1)
    for p_id, polygon_lines in enumerate(polygons):

        for line in polygon_lines:
            ax.plot([line[0][0], line[1][0]], [line[0][1], line[1][1]], c=colors[p_id])


def move_polygon_by_contour(contour_list, v):
    return [[[c[0][0] + v, c[0][1] + v], [c[1][0] + v, c[1][1] + v]] for c in contour_list]


def magnify_polygon_by_contour(contour_list, x):
    return [[[c[0][0] * x, c[0][1] * x], [c[1][0] * x, c[1][1] * x]] for c in contour_list]


def test_check_contours_intersect():
    # Get some polygons from the actual data:
    # The code for creating the hard coded contours from the actual data (the table),
    # for that matter uncomment this or use them in a separate place.
    #    p1_contour_list = table.iloc[20]["contour_list_0.5"]
    #    p1_overlaps = table.iloc[20]["overlaps_0.5"]
    #    p1_first_overlap = p1_overlaps[2]
    #    p2_contour_list = get_overlap_contour_list(p1_first_overlap)
    #    p1_cs = recenter_contours(p1_contour_list)
    #    p2_cs = recenter_contours(p2_contour_list)
    #    print p1_cs
    #    print p2_cs

    p1_contour_list = [[[-9.6, 0.2], [11.4, 0.2]],
                       [[-8.6, 5.2], [9.4, -3.8]],
                       [[-4.6, 10.2], [4.4, -4.8]],
                       [[1.4, 6.2], [1.4, -4.8]],
                       [[3.4, 5.2], [-4.6, -10.8]],
                       [[5.4, 2.2], [-9.6, -5.8]]]
    p2_contour_list = [[[-15.5, -0.7], [32.5, -0.7]],
                       [[-17.5, 9.3], [6.5, -3.7]],
                       [[-4.5, 7.3], [2.5, -3.7]],
                       [[0.5, 3.3], [0.5, -4.7]],
                       [[2.5, 3.3], [-0.5, -3.7]],
                       [[4.5, 1.3], [-11.5, -7.7]]]

    # When two polygons overlap:
    p1_polygon = _create_polygon_lines_by_contours(p1_contour_list)
    p2_polygon = _create_polygon_lines_by_contours(p2_contour_list)
    #    plot_polygons([p1_polygon,p2_polygon])

    check_status = _check_contours_intersect(p1_contour_list, p2_contour_list)
    assert check_status

    # When two polygons a bit overlap:
    p2_contour_list_moved = move_polygon_by_contour(p2_contour_list, 12)

    p2_polygon_moved = _create_polygon_lines_by_contours(p2_contour_list_moved)
    #    plot_polygons([p1_polygon, p2_polygon_moved])

    check_status = _check_contours_intersect(p1_contour_list, p2_contour_list_moved)
    assert check_status

    # When two polygons not overlap:
    p2_contour_list_moved = move_polygon_by_contour(p2_contour_list, 15)

    p2_polygon_moved = _create_polygon_lines_by_contours(p2_contour_list_moved)
    #    plot_polygons([p1_polygon, p2_polygon_moved])

    check_status = _check_contours_intersect(p1_contour_list, p2_contour_list_moved)
    assert (not check_status)

    # When one polygon is inside the other polygon:
    p2_contour_list_magnified = magnify_polygon_by_contour(p2_contour_list, 1.0 / 5.0)

    p2_polygon_magnified = _create_polygon_lines_by_contours(p2_contour_list_magnified)
    #    plot_polygons([p1_polygon, p2_polygon_magnified])

    check_status = _check_contours_intersect(p1_contour_list, p2_contour_list_magnified)
    assert check_status

    # When second polygon is inside the other polygon:
    p2_contour_list_magnified = magnify_polygon_by_contour(p2_contour_list, 5.0)

    p2_polygon_magnified = _create_polygon_lines_by_contours(p2_contour_list_magnified)
    #    plot_polygons([p1_polygon, p2_polygon_magnified])

    check_status = _check_contours_intersect(p1_contour_list, p2_contour_list_magnified)
    assert check_status

    # When the second polygon is perfectly the same as the first polygon:
    p2_contour_list_magnified = magnify_polygon_by_contour(p2_contour_list, 5.0)

    p2_polygon_magnified = _create_polygon_lines_by_contours(p2_contour_list_magnified)
    #    plot_polygons([p1_polygon, p1_polygon])

    check_status = _check_contours_intersect(p1_contour_list, p1_contour_list)
    assert check_status

    # When second polygon is the same as the other polygon but slightly smaller:
    p1_contour_list_magnified = magnify_polygon_by_contour(p1_contour_list, 1.01)

    p1_polygon_magnified = _create_polygon_lines_by_contours(p1_contour_list_magnified)
    #   plot_polygons([p1_polygon, p1_polygon_magnified])

    check_status = _check_contours_intersect(p1_contour_list, p1_contour_list_magnified)
    assert check_status

    # A new kind of points:
    p1_contour_list_t = [[[2500, 3375], [2513, 3375]],
                         [[2496, 3380], [2512, 3371]],
                         [[2500, 3383], [2509, 3368]],
                         [[2505, 3382], [2505, 3371]],
                         [[2507, 3380], [2504, 3372]],
                         [[2509, 3377], [2502, 3373]]]

    p2_contour_list_t = [[[2480, 3386], [2494, 3386]],
                         [[2477, 3391], [2512, 3372]],
                         [[2485, 3389], [2489, 3382]],
                         [[2487, 3388], [2487, 3383]],
                         [[2488, 3388], [2486, 3383]],
                         [[2489, 3387], [2483, 3384]]]

    p1_polygon = _create_polygon_lines_by_contours(p1_contour_list_t)
    p2_polygon = _create_polygon_lines_by_contours(p2_contour_list_t)
    #    plot_polygons([p1_polygon,p2_polygon])

    check_status = _check_contours_intersect(p1_contour_list_t, p2_contour_list_t)
    assert check_status

    # Second new problematic case:
    p1_contour_list_t = [[[2500, 3375], [2513, 3375]],
                         [[2496, 3380], [2512, 3371]],
                         [[2500, 3383], [2509, 3368]],
                         [[2505, 3382], [2505, 3371]],
                         [[2507, 3380], [2504, 3372]],
                         [[2509, 3377], [2502, 3373]]]
    p2_contour_list_t = [[[2454, 3397], [2468, 3397]],
                         [[2451, 3403], [2490, 3382]],
                         [[2461, 3400], [2465, 3394]],
                         [[2463, 3400], [2463, 3393]],
                         [[2464, 3399], [2461, 3392]],
                         [[2465, 3398], [2459, 3395]]]

    p1_polygon = _create_polygon_lines_by_contours(p1_contour_list_t)
    p2_polygon = _create_polygon_lines_by_contours(p2_contour_list_t)
    #    plot_polygons([p1_polygon,p2_polygon])

    check_status = _check_contours_intersect(p1_contour_list_t, p2_contour_list_t)
    assert not check_status

    # 3rd error test from the actual data
    p1_contour_list_t = [[[2500, 3375], [2513, 3375]],
                         [[2496, 3380], [2512, 3371]],
                         [[2500, 3383], [2509, 3368]],
                         [[2505, 3382], [2505, 3371]],
                         [[2507, 3380], [2504, 3372]],
                         [[2509, 3377], [2502, 3373]]]
    p2_contour_list_t = [[[2430, 3402], [2453, 3402]],
                         [[2432, 3408], [2448, 3400]],
                         [[2441, 3405], [2445, 3398]],
                         [[2443, 3404], [2443, 3398]],
                         [[2443, 3403], [2442, 3399]],
                         [[2444, 3403], [2441, 3401]]]

    p1_polygon = _create_polygon_lines_by_contours(p1_contour_list_t)
    p2_polygon = _create_polygon_lines_by_contours(p2_contour_list_t)
    # plot_polygons([p1_polygon, p2_polygon])

    check_status = _check_contours_intersect(p1_contour_list_t, p2_contour_list_t)
    assert (not check_status)

    # 4rd Error case from actuall data:
    p1_contour_list_t = [[[3843, 3283], [3922, 3283]],
                         [[3905, 3284], [3909, 3283]],
                         [[3908, 3283], [3908, 3283]],
                         [[3908, 3284], [3908, 3282]],
                         [[3910, 3284], [3899, 3278]]]
    p2_contour_list_t = [[[3854, 3310], [3858, 3310]],
                         [[3856, 3312], [3857, 3310]],
                         [[3857, 3316], [3857, 3309]],
                         [[3861, 3317], [3856, 3308]],
                         [[3860, 3312], [3856, 3309]]]

    p1_polygon = _create_polygon_lines_by_contours(p1_contour_list_t)
    p2_polygon = _create_polygon_lines_by_contours(p2_contour_list_t)
    plot_polygons([p1_polygon, p2_polygon])

    check_status = _check_contours_intersect(p1_contour_list_t, p2_contour_list_t)
    assert (not check_status)

    # 4rd Error case from actuall data:
    p1_contour_list_t = [[[3843, 3283], [3922, 3283]],
                         [[3905, 3284], [3909, 3283]],
                         [[3908, 3283], [3908, 3283]],
                         [[3908, 3284], [3908, 3282]],
                         [[3910, 3284], [3899, 3278]]]
    p2_contour_list_t = [[[3854, 3310], [3858, 3310]],
                         [[3856, 3312], [3857, 3310]],
                         [[3857, 3316], [3857, 3309]],
                         [[3861, 3317], [3856, 3308]],
                         [[3860, 3312], [3856, 3309]]]

    p1_polygon = _create_polygon_lines_by_contours(p1_contour_list_t)
    p2_polygon = _create_polygon_lines_by_contours(p2_contour_list_t)
    # plot_polygons([p1_polygon, p2_polygon])

    check_status = _check_contours_intersect(p1_contour_list_t, p2_contour_list_t)
    assert (not check_status)

# test_check_contours_intersect()
