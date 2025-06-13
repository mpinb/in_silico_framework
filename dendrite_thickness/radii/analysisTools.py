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

import re
import os
import pandas as pd
import dendrite_thickness.radii as radi
import dendrite_thickness.transformTools as tr


def allData(am050_tr_folder, radi_object):
    # the amPoints_hoc contains the transfromed am points to the hoc coordinates
    # and it is also contains the extracted radi for tht specific points
    # the am_hoc_pairs is actually the pairs of am and hoc points that
    # chose to add the radi from the am to that specific hoc point.
    # the am_hoc_pairs contains the pair of points like this:
    # [[[am point], [hoc point]], ... ]
    # reading extracted radii for the tresholds 025, 050, 075
    # from their corresponding folder and files, and saving them in arrays again.

    # reading transformaed coordinates from am050_tr_folder

    amOutput025 = radi_object.amOutput025
    amOutput050 = radi_object.amOutput050
    amOutput075 = radi_object.amOutput075
    maxZPathList = radi_object.maxZPathList

    trMatrix_hoc = radi_object.trMatrix

    am_hoc_pairs = radi_object.am_hoc_pairs

    am025Paths = [
        amOutput025 + amFile
        for amFile in os.listdir(amOutput025)
        if amFile.endswith(".am")
    ]
    am050Paths = [
        amOutput050 + amFile
        for amFile in os.listdir(amOutput050)
        if amFile.endswith(".am")
    ]
    am075Paths = [
        amOutput075 + amFile
        for amFile in os.listdir(amOutput075)
        if amFile.endswith(".am")
    ]

    amTrPaths = [
        am050_tr_folder + "/" + amFile
        for amFile in os.listdir(am050_tr_folder)
        if amFile.endswith(".am")
    ]

    df = pd.DataFrame()
    df_tr = pd.DataFrame()

    df_beforeFinalTransform = pd.DataFrame()
    df_am_in_hoc_coord = pd.DataFrame()
    df_all = pd.DataFrame()
    file_numbers = len(am050Paths)

    for idx in range(file_numbers):
        # the following are coordinates with respect to
        # the individual slices
        am025_pointsWithRad = tr.read.amFile(am025Paths[idx])
        am050_pointsWithRad = tr.read.amFile(am050Paths[idx])
        am075_pointsWithRad = tr.read.amFile(am075Paths[idx])

        # the following are coordinates with applied transformation
        points_lenght = len(am050_pointsWithRad)

        amTr_pointsWithRad = tr.read.amFile(amTrPaths[idx])
        amPoints_in_hoc = tr.exTrMatrix.applyTransformationMatrix(
            amTr_pointsWithRad, trMatrix_hoc)
        amTr_points = [amTr_pointsWithRad[j][0:3] for j in range(points_lenght)]

        # extract radii
        rads_050 = [am050_pointsWithRad[j][3] for j in range(points_lenght)]
        rads_075 = [am075_pointsWithRad[j][3] for j in range(points_lenght)]

        ## make it a function, as this appears at several points
        amFileName = os.path.basename(am025Paths[idx])
        sliceNumber = re.findall(r'[sS]\d+', amFileName)[0]
        for imagePath in maxZPathList:
            imageName = os.path.basename(imagePath)
            if sliceNumber in imageName:
                sliceName = imageName
                break

        # putting the data from one slice into a temporary data frame
        df_temp = pd.DataFrame(am025_pointsWithRad,
                               columns=["x", "y", "z", "radius 025"])

        # adding the slice name to all points of the temporary data frame of one slice
        df_temp.insert(0, "slice", sliceName)

        # adding the different treshold of radii of the slice to the temporary data frame
        df_temp["radius 050"] = rads_050
        df_temp["radius 075"] = rads_075

        # append the temporary data frame to the whole cell data frame
        df = df.append(df_temp)

        # adding the coordinates of the transformed am files to a new temporary data frame
        df_tr_temp = pd.DataFrame(amTr_points, columns=["x_hx", "y_hx", "z_hx"])

        # appending the new temporary data frame of tr points to the whole cell tr data frame
        df_tr = df_tr.append(df_tr_temp)

    # Join the two data frame for tr points and the raw points together
    df_beforeFinalTransform = pd.concat([df, df_tr], axis=1)

    am_in_hoc_coord = [point[0:3] for point in amPoints_in_hoc]
    df_am_in_hoc_coord = pd.DataFrame(am_in_hoc_coord,
                                      columns=["x_hoc", "y_hoc", "z_hoc"])

    # df_all = pd.concat([df_beforeFinalTransform, df_am_in_hoc_coord.reindex(df_beforeFinalTransform.index)], axis=1)

    # the below process results as the same above preoces, just keep it pls
    # later use
    df_all = df_beforeFinalTransform.join(df_am_in_hoc_coord, how='outer')
    return df_all
