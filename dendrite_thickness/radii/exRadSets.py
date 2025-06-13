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

import os
import re
import dendrite_thickness.transformTools as tr
from dendrite_thickness import radii as radi
import SimpleITK as sitk


class RadiusCalculatorForManyFiles:
    """
    This module extracts all of the radii sets, each set corresponds to an
    .am file, and writes the calculated radii in new .am files in a new folder.

    Inputs:
    path_to_am: path to the folder contains the initial .am files without radius.
    path_to_tif: path to the folder contains the tif images corresponds to .am
    files.
    path_to_output: path to the output folder and its name.

    Outputs:
    1. calculats radii sets, and puts each set inside its corresponding .am file
    inside the given output folder path.
    """

    def __init__(self,
                 xyResolution=0.092,
                 zResolution=0.5,
                 xySize=20,
                 numberOfRays=10,
                 tresholdPercentage=0.5,
                 numberOfRaysForPostMeasurment=20):
        self.xyResolution = xyResolution
        self.zResolution = zResolution
        self.xySize = xySize
        self.numberOfRays = numberOfRays
        self.tresholdPercentage = tresholdPercentage

        self.rayLengthPerDirectionOfImageCoordinatesForPostMeasurment = 0.50 / xyResolution  # self.rayLengthPerDirectionOfImageCoordinates/10
        self.numberOfRaysForPostMeasurment = numberOfRaysForPostMeasurment

        self.radiusCalculator = radi.calcRad.RadiusCalculator(
            xyResolution=self.xyResolution,
            zResolution=self.zResolution,
            xySize=self.xySize,
            numberOfRays=self.numberOfRays,
            tresholdPercentage=self.tresholdPercentage)

    def exRadSets(self,
                  path_to_am,
                  path_to_tif,
                  path_to_output_folder,
                  postMeasurment=False):
        """
        extraxt radii sets of bunch of files from the folder of path_to_am
        and writ them to and output folder
        """

        if (os.path.isdir(path_to_am) and os.path.isdir(path_to_tif)):
            for spatialGraphFile in os.listdir(path_to_am):
                if spatialGraphFile.endswith(".am"):
                    points = self.readPoints(
                        os.path.join(path_to_am, spatialGraphFile))
                    if points == "error":
                        continue
                    spatialGraphIndicator = re.findall(r'[sS]\d+',
                                                       spatialGraphFile)[0]
                    outputFile = os.path.join(
                        path_to_output_folder, spatialGraphIndicator + "_with_r.am")
                    for imageFile in os.listdir(path_to_tif):
                        if imageFile.startswith(spatialGraphIndicator):
                            image = self.readImage(path_to_tif + imageFile)
                            # result = radi.radius.getRadiiHalfMax(image, points)
                            result = self.radiusCalculator.getProfileOfThesePoints(
                                image, points, postMeasurment)
                            print(imageFile)
                            self.writeResult(
                                os.path.join(path_to_am, spatialGraphFile,
                                             outputFile, result))
                            break
        else:
            points = self.readPoints(path_to_am)
            if points == "error":
                return "error"
            amFileName = os.path.basename(path_to_am)
            outputFile = os.path.join(path_to_output_folder, amFileName)
            imageFile = path_to_tif
            image = self.readImage(imageFile)
            result = self.radiusCalculator.getProfileOfThesePoints(
                image, points, postMeasurment)
            print(" ")
            print("program ran for the file:" + imageFile)
            self.writeResult(path_to_am, outputFile, result)
        return "safe"

    def readImage(self, imageFile):
        '''reading image file '''
        imageFileReader = sitk.ImageFileReader()
        imageFileReader.SetFileName(imageFile)
        image = imageFileReader.Execute()
        return image

    def readPoints(self, dataFile):
        ''' return points of a am file, by using the function "getSpatialGraphPoints"'''
        try:
            points = radi.spatialGraph.getSpatialGraphPoints(dataFile)
        except IOError as fnf_error:
            print(" ")
            print(fnf_error)
            print("for the file:")
            print(dataFile)
            print("in readPoints()")
            return "error"
        except UnicodeError as ucode_error:
            print(" ")
            print(ucode_error)
            print("for the file:")
            print(dataFile)
            print("in readPoints()")
            return "error"
        except ValueError as val_error:
            print(" ")
            print(val_error)
            print("for the file:")
            print(dataFile)
            print("in readPoints()")
            return "error"


#       points = list(map(lambda x: map(lambda y: int(y/0.092), x), points))
        points = [
            tr.read.convert_point(x, 1.0 / 0.092, 1.0 / 0.092, 1.0)
            for x in points
        ]

        return points

    def writeResult(self, inputDataFile, outputDataFile, result):
        '''This function will write the result of the extracted radii to final am file '''
        radii = result
        radii = [r * 0.092 for r in radii]
        try:
            radi.spatialGraph.write_spatial_graph_with_thickness(
                inputDataFile, outputDataFile, radii)
        except IOError as fnf_error:
            print(" ")
            print(fnf_error)
            print("for the file:")
            print(dataFile)
            print("in wirteResult()")
            return "error"
        except UnicodeError as ucode_error:
            print(" ")
            print(ucode_error)
            print("for the file:")
            print(dataFile)
            print("in wirteResult()")
            return "error"
        except ValueError as val_error:
            print(" ")
            print(val_error)
            print("for the file:")
            print(dataFile)
            print("in wirteResult()")
            return "error"
