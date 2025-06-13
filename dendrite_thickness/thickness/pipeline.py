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

import dask
from dask import distributed

from . import thickness as th
from . import transformation as tr
from . import IO
from . import utils as u
from . import analysis as an
from dask.distributed import wait
import time


class SliceData:

    def __init__(self, slice_name=None, slice_threshold=None):
        self.slice_name = slice_name
        self.am_file_path = None
        self.image_file_path = None
        self.image_stack = {}
        self.output_path = None
        self.am_object = None
        self.am_points = None
        self.am_points_with_applied_am_file_transform = None
        self.am_points_in_hoc_coordinate_system = None
        self.slice_thicknesses_object = None
        self.transformation_object = None
        self.slice_threshold = slice_threshold
        self.image_stack_input_path = None
        self.image_stack = None

    def setup_am_file(self, path):
        if self.output_path is None:
            raise RuntimeError(
                "Please first set_output_path by set_output_path('path')")
        self.am_file_path = path
        self.am_object = IO.Am(self.am_file_path, self.output_path)
        self.am_points = self.am_object.all_data[
            "POINT { float[3] EdgePointCoordinates }"]
        if self.am_object.transformation_matrix_exist:
            tr_object = tr.AffineTransformation()
            tr_object.set_transformation_matrix(
                self.am_object.transformation_matrix)
            self.am_points_with_applied_am_file_transform = tr_object.transform_points(
                self.am_points)
        else:
            self.am_points_with_applied_am_file_transform = self.am_points

    def set_image_file_path(self, path):
        self.image_file_path = path

    def set_output_path(self, path):
        self.output_path = path

    def set_slice_name(self, slice_name=None):
        if slice_name is not None:
            self.slice_name = slice_name
        else:
            if self.image_file_path:
                self.slice_name = u.get_slice_name(self.am_file_path,
                                                   self.image_file_path)
            elif self.image_stack_input_path:
                self.slice_name = u.get_slice_name(self.am_file_path,
                                                   self.image_stack_input_path)
            else:
                raise ValueError(
                    'Neither image_file_path nor image_stack_input_path are set. '
                    + 'Cannot infer slice name.')

    def set_image_stack(self, input_path, subfolders=None):
        self.image_stack_input_path = input_path
        self.image_stack = u.create_image_stack_dict_of_slice(
            input_path, subfolders)

    def compute(self, xy_resolution, z_resolution,
                ray_length_front_to_back_in_micron, number_of_rays,
                threshold_percentage, max_seed_correction_radius_in_micron, _3d,
                image_stack, slice_name):
        slice_thicknesses_object = th.ThicknessExtractor(
            self.am_points, self.image_file_path, xy_resolution, z_resolution,
            ray_length_front_to_back_in_micron, number_of_rays,
            threshold_percentage, max_seed_correction_radius_in_micron, _3d,
            image_stack, slice_name)
        self.slice_thicknesses_object = slice_thicknesses_object
        # data element for am_object must be themselves a list. That is why we put each thickness to a list in below.
        # self.am_object.add_data("POINT { float thickness }",
        #                         [[thickness] for thickness in self.slice_thicknesses_object.thickness_list])
        # self.am_object.write()


class ExtractThicknessPipeline:

    def __init__(self,
                 xy_resolution=0.092,
                 z_resolution=0.5,
                 number_of_rays=36,
                 ray_length_front_to_back_in_micron=20,
                 max_seed_correction_radius_in_micron=10):

        # ---- flags and settings
        self._parallel = False
        self.client = None
        self._save_data = True
        self.save_data = None
        self._3D = False
        # ---- files and folders
        self.hoc_file = None
        self.hoc_object = None
        self.am_paths = []
        self.tif_paths = []
        self.output_folder = None
        # --- thickness extractor class parameters:

        self.xy_resolution = xy_resolution
        self.z_resolution = z_resolution
        self.number_of_rays = number_of_rays
        self.ray_length_front_to_back_in_micron = ray_length_front_to_back_in_micron
        self.max_seed_correction_radius_in_micron = max_seed_correction_radius_in_micron

        self.default_threshold = 0.5
        self.thresholds_list = [self.default_threshold]

        # --- objects and dicts
        self.am_tif = {}
        self.all_slices = {}
        self.all_am_points = []
        self.all_am_points_in_hoc_coordinate_system = []
        self.all_thicknesses = {}
        self.image_stack_folder_paths = None
        self.image_stack_folder_paths_subfolders = None
        # --- transformation
        # am_to_hoc_bijective_points are set/list/dict of 4 am_points from
        self.am_to_hoc_bijective_points = None

    def set_am_paths_by_list(self, am_paths_list):
        self.am_paths = am_paths_list

    def set_am_paths_by_folder(self, folder_path_to_am_files):
        self.am_paths = u.get_files_by_folder(folder_path_to_am_files,
                                              file_extension="am")

    def set_am_paths_by_hx(self, folder_path_to_hx_file):
        self.am_paths = u.get_am_paths_from_hx(folder_path_to_hx_file)

    def set_output_path(self, path_to_output_folder):
        self.output_folder = path_to_output_folder
        if self.hoc_object is not None:
            self.hoc_object.output_path = self.output_folder

    def set_hoc_file(self, path_to_hoc_file):
        self.hoc_file = path_to_hoc_file
        if self.output_folder is None:
            raise RuntimeError("Please first set_output_path")
        else:
            self.hoc_object = IO.Hoc(
                self.hoc_file, self.output_folder + "/" +
                u.get_file_name_from_path(self.hoc_file))

    def set_tif_paths_by_list(self, tif_paths_list):
        self.tif_paths = tif_paths_list

    def set_tif_paths_by_folder(self, folder_path_to_tif_files):
        self.tif_paths = u.get_files_by_folder(folder_path_to_tif_files,
                                               file_extension="tif")

    def set_tif_3d_stack_by_folders(self, folder_paths, subfolders=None):
        self._3D = True
        self.image_stack_folder_paths = folder_paths
        self.image_stack_folder_paths_subfolders = subfolders

    # TODO: EG: to put in init with defaults, set_thresholds, set_thickness..
    def set_thresholds(self, thresholds_list):
        """
        :param thresholds_list: A list contains thresholds values for extracting thicknesses
        :return: A setter function, No return, if not set the default value of 0.5 will be used
        """
        self.thresholds_list = thresholds_list

    def set_am_to_hoc_transformation_by_list(self, bi_points):
        self.am_to_hoc_bijective_points = bi_points

    def set_am_to_hoc_transformation_by_landmarkAscii(self, input_path):
        bijective_list_points = IO.read_landmark_file(input_path)
        self.am_to_hoc_bijective_points = [
            list(p) for p in bijective_list_points
        ]

    def set_bijective_points_automatically(self):
        """ TODO: This function will call the poor function that we developed and not working well"""
        pass

    def set_client_for_parallelization(self, client):
        self.client = client
        print(self.client)
        self._parallel = True

    def run(self):
        self._run1()
        df = self._run2()
        return df

    def _run1(self):
        self._initialize_project()
        self._setup_slice_objects()
        delays = self._extract_thicknesses()

        if self._parallel:
            results = None
            if self._save_data:
                results = self.save_data.load()
            if results is None:
                futures = self.client.compute(delays)
                self.futures = futures
                wait(futures)
                results = self.client.gather(futures)
                self.save_data.dump(results)
            self._update_slice_objects_with_future_values(results)

    def _run2(self):
        self._write_am_outputs()
        self._transform_points()
        self._stacking_all_slices()
        self._update_hoc_file_with_thicknesses()
        self._compute_all_data_table()
        # return data_table  # this can get big

    def _initialize_project(self):
        print("---- initialize project ----")
        if self.output_folder is None:
            self.output_folder = u.make_directories(self.output_folder)
        for threshold in self.thresholds_list:
            u.make_directories(self.output_folder + "/" + str(threshold))
        if self._save_data:
            data_file = self.output_folder + "/" + "data_file"
            self.save_data = u.SaveData(data_file)

    def _setup_slice_objects(self):
        print("---- setup slice objects ----")
        thresholds = self.thresholds_list
        if self.am_paths is None or self.tif_paths is None:
            raise RuntimeError("You need to set am and tif paths")
        for threshold in thresholds:
            all_slices_in_threshold = {}
            print("In threshold: " + str(threshold))
            for am_file in self.am_paths:
                slice_object = SliceData(slice_threshold=threshold)
                slice_object.set_output_path(self.output_folder + "/" +
                                             str(threshold) + "/" +
                                             u.get_file_name_from_path(am_file))
                slice_object.setup_am_file(am_file)
                if self._3D:
                    slice_object.set_image_stack(
                        u.get_am_image_match(
                            [am_file], self.image_stack_folder_paths)[am_file],
                        self.image_stack_folder_paths_subfolders)
                else:
                    slice_object.set_image_file_path(
                        u.get_am_image_match([am_file],
                                             self.tif_paths)[am_file])
                slice_object.set_slice_name()
                print("--------")
                print("Setting up slice:" + slice_object.slice_name)
                all_slices_in_threshold[slice_object.slice_name] = slice_object
            self.all_slices[threshold] = all_slices_in_threshold

    def _extract_thicknesses(self):
        print("---- extract thicknesses ----")
        thresholds = self.thresholds_list
        delays = []
        s = self
        for threshold in thresholds:
            for slice_name in sorted(s.all_slices[threshold]):
                slice_object = s.all_slices[threshold][slice_name]
                if s._parallel:
                    delay = _parallel_helper(
                        slice_object.am_points, slice_object.image_file_path,
                        s.xy_resolution, s.z_resolution,
                        s.ray_length_front_to_back_in_micron, s.number_of_rays,
                        threshold, s.max_seed_correction_radius_in_micron,
                        s._3D, slice_object.image_stack,
                        slice_object.slice_name)
                    delays.append(delay)
                else:
                    slice_object.compute(s.xy_resolution, s.z_resolution,
                                         s.ray_length_front_to_back_in_micron,
                                         s.number_of_rays, threshold,
                                         s.max_seed_correction_radius_in_micron,
                                         s._3D, slice_object.image_stack,
                                         slice_object.slice_name)

        return delays

    def _transform_points(self):
        print("---- transform am_points ----")
        at = tr.AffineTransformation()
        at.set_transformation_matrix_by_aligned_points(
            self.am_to_hoc_bijective_points[::2],
            self.am_to_hoc_bijective_points[1::2])
        for threshold in self.thresholds_list:
            all_slices_with_same_threshold = self.all_slices[threshold]
            for key in sorted(all_slices_with_same_threshold.keys()):
                slice_object = all_slices_with_same_threshold[key]
                transformed_points = at.transform_points(
                    slice_object.am_points_with_applied_am_file_transform,
                    forwards=True)
                slice_object.am_points_in_hoc_coordinate_system = transformed_points
                slice_object.am_to_hoc_transformation_object = at

    def _update_hoc_file_with_thicknesses(self):

        print("---- update hoc file with thicknesses ----")
        total_points = len(self.hoc_object.all_data["am_points"])
        for idx, hoc_point in enumerate(self.hoc_object.all_data["am_points"]):
            start = time.time()
            nearest_point_index = self.all_am_points_in_hoc_coordinate_system.index(
                u.get_nearest_point(
                    hoc_point, self.all_am_points_in_hoc_coordinate_system))
            self.hoc_object.all_data["thicknesses"].append(self.all_thicknesses[
                self.default_threshold][nearest_point_index])
            end = time.time()
            if not idx % 100:
                print("time:" + str(end - start))
                print("point " + str(idx + 1) + "from " + str(total_points))
                print("------------")
        self.hoc_object.update_thicknesses()

    def _compute_all_data_table(self):
        print("---- compute all data table ----")
        return an.get_all_data_output_table(self.all_slices,
                                            self.default_threshold)

    def _stacking_all_slices(self):
        print("---- stacking all slices ----")
        all_slices_with_default_threshold = self.all_slices[
            self.default_threshold]
        self.all_am_points = [
            point for key in sorted(all_slices_with_default_threshold.keys())
            for point in all_slices_with_default_threshold[key].am_points
        ]
        self.all_am_points_with_applied_am_file_transform = [
            point for key in sorted(all_slices_with_default_threshold.keys())
            for point in all_slices_with_default_threshold[key].
            am_points_with_applied_am_file_transform
        ]

        self.all_am_points_in_hoc_coordinate_system = [
            tr_points
            for key in sorted(all_slices_with_default_threshold.keys())
            for tr_points in all_slices_with_default_threshold[key].
            am_points_in_hoc_coordinate_system
        ]
        for threshold in self.thresholds_list:
            all_slices_with_same_threshold = self.all_slices[threshold]
            self.all_thicknesses = {
                threshold: [
                    all_slices_with_same_threshold[key].
                    slice_thicknesses_object.thickness_list[index]
                    for key in sorted(all_slices_with_same_threshold.keys())
                    for index in range(
                        len(all_slices_with_same_threshold[key].am_points))
                ]
            }

        print("Number of all am_points: " + str(len(self.all_am_points)))
        assert len(self.all_am_points) == len(
            self.all_am_points_in_hoc_coordinate_system) == len(
                list(self.all_thicknesses.values())[0])
        assert len(self.all_thicknesses) == len([
            1
            for thicknesses_in_threshold in list(self.all_thicknesses.values())
            if len(thicknesses_in_threshold) == len(
                list(self.all_thicknesses.values())[0])
        ])

    def _write_am_outputs(self):
        print("---- write am outputs ----")
        s = self
        for threshold in s.thresholds_list:
            for slice_name in sorted(s.all_slices[threshold]):
                ### urgendt todo: update of thickness list should not be done here1!!!!
                slice_object = s.all_slices[threshold][slice_name]
                slice_object.am_object.add_data(
                    "POINT { float thickness }",
                    [[thickness] for thickness in
                     slice_object.slice_thicknesses_object.thickness_list])
                slice_object.am_object.write()
                # slice_object.write_output(slice_object.am_points)

    def _update_slice_objects_with_future_values(self, results):
        print("---- update slice objects with future values ----")
        for result in results:
            thicknesses_object = result
            threshold = thicknesses_object.threshold_percentage
            for slice_name in sorted(self.all_slices[threshold]):
                slice_object = self.all_slices[threshold][slice_name]
                if slice_object.slice_name == thicknesses_object.slice_name:
                    slice_object.slice_thicknesses_object = thicknesses_object


@dask.delayed
def _parallel_helper(points, image_file_path, xy_resolution, z_resolution,
                     ray_length_front_to_back_in_micron, number_of_rays,
                     threshold, max_seed_correction_radius_in_micron, _3d,
                     image_stack, slice_name):
    slice_thicknesses_object = th.ThicknessExtractor(
        points, image_file_path, xy_resolution, z_resolution,
        ray_length_front_to_back_in_micron, number_of_rays, threshold,
        max_seed_correction_radius_in_micron, _3d, image_stack, slice_name)

    return slice_thicknesses_object


# _parallel_helper_delayed = dask.delayed(_parallel_helper)
