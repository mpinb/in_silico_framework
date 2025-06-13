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

import pandas as pd


def get_all_data_output_table(all_slices, default_threshold):
    df_out = pd.DataFrame()

    df_all_slices_points = pd.DataFrame()
    d_ = all_slices[default_threshold]
    for key in sorted(d_.keys()):
        slice_object = d_[key]
        df_individual_slice_points = pd.DataFrame(
            slice_object.am_points, columns=["x_slice", "y_slice", "z_slice"])
        df_individual_slice_points_applied_transform = pd.DataFrame(
            slice_object.am_points_with_applied_am_file_transform,
            columns=[
                "x_applied_transform", "y_applied_transform",
                "z_applied_transform"
            ])
        df_individual_slice_tr_points = pd.DataFrame(
            slice_object.am_points_in_hoc_coordinate_system,
            columns=["x_hoc_system", "y_hoc_system", "z_hoc_system"])
        df_individual_slice = pd.concat([
            df_individual_slice_points,
            df_individual_slice_points_applied_transform,
            df_individual_slice_tr_points,
        ],
                                        axis=1)
        df_individual_slice['slice'] = slice_object.slice_name
        df_all_slices_points = pd.concat(
            [df_all_slices_points, df_individual_slice])

    df_all_data = pd.DataFrame()
    for threshold in sorted(all_slices.keys()):
        df_individual_threshold = pd.DataFrame()
        for key in sorted(all_slices[threshold].keys()):
            slice_object = all_slices[threshold][key]
            all_data = slice_object.slice_thicknesses_object.all_data
            all_data_keys = sorted(all_data.keys())
            df = pd.DataFrame.from_dict(all_data)
            df = df[all_data_keys]
            df = df.T
            df.columns = [c + '_' + str(threshold) for c in df.columns]
            df_individual_threshold = pd.concat([df_individual_threshold, df])
        df_all_data = pd.concat([df_all_data, df_individual_threshold], axis=1)

    return pd.concat([df_all_slices_points, df_all_data], axis=1)
