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
import numpy as np
import dendrite_thickness.radii as radi
import dendrite_thickness.transformTools as tr
import re
import pandas as pd
import time
import dask


def convert_point(p, x_res=0.092, y_res=0.092, z_res=1.0):
    '''todo: use this function consistently to convert 
    pixel locations to coordinates!'''
    out = []
    scaling = [x_res, y_res, z_res]
    for lv, pp in enumerate(p):
        try:
            s = scaling[lv]
        except IndexError:
            s = 1
        out.append(pp * s)
    return out


@dask.delayed
def _paralellization_helper(radiiObject,
                            amPth,
                            imageFilePath,
                            amOutput,
                            postMeasurment='yes'):
    radiiObject.exRadSets(amPth, imageFilePath, amOutput, postMeasurment='yes')
    sliceName = getSliceName(amPth, imageFilePath)
    print(sliceName)
    radiiDetails = dict()
    radiiDetails["Slice name"] = sliceName

    orig_temp = radiiObject.radiusCalculator.orig_pointsWithIntensity
    pm_temp = radiiObject.radiusCalculator.pm_pointsWithIntensity
    ray_points = radiiObject.radiusCalculator.counterList
    # cave: this needs to be moved to a place wherer we are aware of the x/y/z resolution!
    # Here, the default (0.092 / 0.092 / 0.5) is used, but that might change from usecase to usecase.

    orig_temp = [(convert_point(x[0]), x[1]) for x in orig_temp]
    pm_temp = [(convert_point(x[0]), x[1]) for x in pm_temp]

    radiiDetails["Treshold"] = radiiObject.tresholdPercentage
    radiiDetails["Inten. orig points"] = orig_temp
    radiiDetails["Inten. post points"] = pm_temp
    radiiDetails["Ray points"] = ray_points

    return radiiDetails


def getSliceName(amPth, imageFilePath):
    am = os.path.basename(amPth)
    imageName = os.path.basename(imageFilePath)
    spatialGraphName = re.findall(r'[sS]\d+', am)[0]
    sliceNumber = int(re.findall(r'\d+', spatialGraphName)[0])
    if spatialGraphName in imageName:
        return sliceNumber
    else:
        return "No name found"


class RadiiPipeline:
    """
    Inputs:
    1. amInputPathList: an array contains the paths of am files
    2. maxZPathList: an array contains list of path of maxZ projection image files.
    3. outputFolder: Is a path to the outputFolder that the final result will be written.
    4. amWithRad: if provided then the class can be use to run the findTransformation method.

    """

    def __init__(self,
                 amInputPathList,
                 maxZPathList,
                 hocFile,
                 outputFolder,
                 amWithRad="default"):
        self.amInputPathList = amInputPathList
        self.maxZPathList = maxZPathList
        self.hocFile = hocFile
        self.amWithRad = amWithRad
        self.spanFactor = 10.0

        self.outputDirectory = self.initOutputDirectory(outputFolder)

        self.amWithErrorsDirectory = os.path.join(self.outputDirectory, "amWithErrors")
        self.amOutput025 = os.path.join(self.outputDirectory, "am025")
        self.amOutput050 = os.path.join(self.outputDirectory, "am050")
        self.amOutput075 = os.path.join(self.outputDirectory, "am075")
        self.hocFileOutput = os.path.join(self.outputDirectory, "hocFileWithRad.hoc")
        self.amWithUcrs = {}
        self.points025 = {}
        self.points050 = {}
        self.points075 = {}
        self.amPointsTransformed_hoc = []
        self.am_hoc_pairs = []
        self.trMatrix = []
        self.delayeds = []

    def runRayBurstOnSlices(self, tr025=True, tr050=True, tr075=True):
        """
        Will call the extrationRadii method for different Treshhold.
        each tresholdPercentage can be optionally removed by making its parameter false:
        like tr025 = Fales

        """
        self.createOutputDirectories()
        return self.extractRadii(tr025, tr050, tr075)
        res = self.hocFile
        return res

    def initOutputDirectory(self, folder):
        """
        The ouptut directory need to be initilize to have different folders for each tresholdPercentage.
        if the folders are exist the function will not touch them
        """
        cellPath = os.path.dirname(os.path.dirname(self.amInputPathList[0]))
        cellFolderName = os.path.basename(cellPath)
        outputDirectory = os.path.join(folder, cellFolderName)
        if not (os.path.isdir(outputDirectory)):
            os.mkdir(outputDirectory)
        return outputDirectory

    def createOutputDirectories(self):
        '''will creat the output directory with the name of the cell'''

        if not os.path.isdir(self.amWithErrorsDirectory):
            os.mkdir(self.amWithErrorsDirectory)

        if not os.path.isdir(self.amOutput025):
            os.mkdir(self.amOutput025)

        if not os.path.isdir(self.amOutput050):
            os.mkdir(self.amOutput050)

        if not os.path.isdir(self.amOutput075):
            os.mkdir(self.amOutput075)

    def extractRadii(self, tr025=True, tr050=True, tr075=True):
        '''will handle the calling of exRadSets function for different tresholdPercentages '''
        if not os.path.isdir(self.amWithErrorsDirectory):
            os.mkdir(self.amWithErrorsDirectory)

        delayeds = []
        for idx, amPth in enumerate(self.amInputPathList):
            am = os.path.basename(amPth)
            spatialGraphName = re.findall(r'[sS]\d+', am)[0]
            for imageFilePath in self.maxZPathList:
                imageName = os.path.basename(imageFilePath)
                if spatialGraphName in imageName:
                    if (tr025):
                        radi025 = radi.exRadSets.RadiusCalculatorForManyFiles(
                            tresholdPercentage=0.25)
                        d = _paralellization_helper(radi025,
                                                    amPth,
                                                    imageFilePath,
                                                    self.amOutput025,
                                                    postMeasurment='yes')
                        delayeds.append(d)

                    if (tr050):
                        radi050 = radi.exRadSets.RadiusCalculatorForManyFiles(
                            tresholdPercentage=0.5)
                        d = _paralellization_helper(radi050,
                                                    amPth,
                                                    imageFilePath,
                                                    self.amOutput050,
                                                    postMeasurment='yes')
                        delayeds.append(d)

                    if (tr075):
                        radi075 = radi.exRadSets.RadiusCalculatorForManyFiles(
                            tresholdPercentage=0.75)
                        d = _paralellization_helper(radi075,
                                                    amPth,
                                                    imageFilePath,
                                                    self.amOutput075,
                                                    postMeasurment='yes')
                        delayeds.append(d)

                    #radi025.exRadSets(amPth, imageFilePath, self.amOutput025, postMeasurment='yes')

                    break
        return delayeds

    def extractUncertainties(self):
        '''extract uncertainties for diff. tresholds and add them to file by calling addUncertainties'''
        self.readExtractedRadii()
        self.amWithUcrs = radi.calcError.addUncertainties(
            self.points050, self.points025, self.points075)
        self.writeUncertainties()

    def readExtractedRadii(self):
        '''will hanld reading ampoints with radii and uncertainties for diff. tresholds'''
        print(self.amOutput025)
        self.allAmPointsWithRadius025, self.points025 = tr.read.multipleAmFiles(
            self.amOutput025)
        self.allAmPointsWithRadius050, self.points050 = tr.read.multipleAmFiles(
            self.amOutput050)
        self.allAmPointsWithRadius075, self.points075 = tr.read.multipleAmFiles(
            self.amOutput075)

    def writeUncertainties(self):
        '''will write uncertainties in the output files'''
        for amInputPath in self.amInputPathList:
            tr.write.multipleAmFilesWithRadiusAndUncertainty(
                amInputPath, self.amWithErrorsDirectory, self.amWithUcrs)

    def getAmFileWithRad(self):
        '''check if it need to ger amFile or not.'''
        assert self.amWithRad != "Default"
        amFile = self.amWithRad
        return amFile

    def dataAnalysis(self, amTrFolder):
        return radi.analysisTools.allData(amTrFolder, self)

    # def allData(self):
    #     # reading extracted radii for the tresholds 025, 050, and 075
    #     # from their corresponding folder and files, and saving them in arrays again.
    #     colNames = ["x", "y", "z", "slice", "025", "050", "075"]
    #     am025Paths = [self.amOutput025 + amFile for amFile in os.listdir(self.amOutput025) if amFile.endswith(".am")]
    #     am050Paths = [self.amOutput050 + amFile for amFile in os.listdir(self.amOutput050) if amFile.endswith(".am")]
    #     am075Paths = [self.amOutput075 + amFile for amFile in os.listdir(self.amOutput075) if amFile.endswith(".am")]

    #     for amPath in am050Paths:
    #         am050_pointsWithRad = tr.read.am(amPath)
    #         amFileName = os.path.basename(amPath)
    #         sliceNumber = re.findall(r'[sS]\d+', amFileName)[0]
    #         for imagePath in self.maxZPathList:
    #             imageName = os.path.basename(imagePath)
    #             if sliceNumber in imageName:
    #                 sliceName = imageName
    #                 break
    #         point5d = [point4d.append(sliceName) for point4d in am050_pointsWithRad]

    #     print(amPathsList)
    #     # df = pandas.read_csv('hrdata.csv',
    #     # names=['Employee', 'Hired', 'Salary', 'Sick Days'])
    #     # df.to_csv('hrdata_modified.csv')

    #         radi050=radi.exRadSets.RadiusCalculatorForManyFiles(tresholdPercentage=0.50)
    #         for idx, amPth in enumerate(self.amInputPathList):
    #             am = os.path.basename(amPth)
    #             spatialGraphName = re.findall(r'[sS]\d+', am)[0]
    #             for imageFilePath in self.maxZPathList:
    #                 imageName = os.path.basename(imageFilePath)
    #                 if spatialGraphName in imageName:
    #                     radi050.exRadSets(amPth, imageFilePath, self.amOutput050, postMeasurment='yes')
    #                     break

    def findTransformation(self,
                           amWithRad,
                           spanFactor=10.0,
                           addRadii=True,
                           findingPairPoints=True,
                           pairPoints=[]):
        """
        find the transformation between amFile and HocFile.
        inputs:
        1. amWithRad: final Provided amFile which contains the radii of points.
        2. spanFactor: Default value is 10.0, it will adjust the choosing of the edges by a span.
        3. addRadii: if it provided False it will not go to the step finding the pairs bbetween transformedPoints
        and HocPoints, this will lead to faster run for experimenting the transformion quality.
        4. auto: If true the algorithm will find pairs of points between two morphologies automatically by itself.
        otherwise it will use the pairPoints array as a parameter to find the transformation between two morphologies.
        5. pairPoints: if you pass the auto false then you need to pass the pairPoints which you prepared manually before.
        the pairpoints format is assume to be like below.
        [[a1,b1], [a2,b2], [a3,b3], [a4,b4]]
        a1 is the point number 1 from the morphology a, and b1 is a the point in morphology b which is corresponding 
        to point a1. You need to exactly prepare 4 points in morphology a and their corresponding points in morphology b.
        outputs:
        1. provide the final hocPointsWithRad if addRadii is true.
        2. it will write the amTransformed and egAm and egHoc in text format files. These are by their order contain
        the transformed am points, choosed am edges, and choosed hoc edges.

        """

        assert self.amWithRad != "Default"
        if (findingPairPoints == False and pairPoints == []):
            raise ValueError(
                "When you adjust the input findingPairPoints) to false you need to provide the pairPoints Manuallly and pass it through the array pairPoints"
            )

        self.amWithRad = amWithRad
        self.spanFactor = spanFactor

        pointsWithRadius = tr.read.hocFileComplete(self.hocFile)
        #  pointsWithRadius = tr.read.hocFileReduced(self.hocFile)
        hocPointsSet = []
        pairs = []

        for el in pointsWithRadius:
            hocPointsSet.append([el[0], el[1], el[2]])

        amFile = self.amWithRad

        amSet = radi.spatialGraph.getSpatialGraphPoints(amFile)

        numberOfEdges = 2

        src_hoc = []
        dst_am = []

        if (findingPairPoints):
            matchedSet = tr.getDistance.matchEdges(hocPointsSet, amSet,
                                                   numberOfEdges, spanFactor)

            for point in matchedSet:
                src_hoc.append(point[0].start)
                src_hoc.append(point[0].end)

                dst_am.append(point[1].start)
                dst_am.append(point[1].end)

        else:
            src_hoc = pairPoints[1::2]
            print(src_hoc)
            dst_am = pairPoints[::2]
            print("the dst_am file")
            print(dst_am)

        print("In the calculations of the transformation matrix")
        trMatrix2 = tr.exTrMatrix.getTransformation(dst_am, src_hoc)

        self.trMatrix = trMatrix2
        print(amFile)
        amPoints4D = tr.read.amFile(amFile)

        print("Applying the transofrmation matrix to the initial am points")
        trAmPoints4D = tr.exTrMatrix.applyTransformationMatrix(
            amPoints4D, trMatrix2)

        hocPointsComplete = tr.read.hocFileComplete(self.hocFile)
        hocSet = []
        for el in hocPointsComplete:
            hocSet.append([el[0], el[1], el[2]])

        self.amPointsTransformed_hoc = trAmPoints4D

        print(
            "In the process of finding pairs in between hoc file and the transformed points to add radi to hocpoint"
        )
        startTime = time.time()
        if addRadii:
            pairs = radi.addRadii.findPairs(trAmPoints4D, hocSet)
            self.am_hoc_pairs = pairs
        endTime = time.time()
        print(endTime - startTime)

        startTime = time.time()
        hocWithRad = []
        newHPoint = []

        for pair in pairs:
            newHPoint = pair[1]
            dual = pair[0]
            newHPoint.append(dual[3])
            hocWithRad.append(newHPoint)
            newHPoint = []

        endTime = time.time()
        print(endTime - startTime)

        if (addRadii):
            print("writing the final result in the output hocFile")
            tr.write.hocFile(self.hocFile, self.hocFileOutput, hocWithRad)

        egHocFile = os.path.join(self.outputDirectory, '/egHoc.txt')
        egAmFile = os.path.join(self.outputDirectory, '/egAm.txt')
        with open(egHocFile, 'w') as f:
            for idx in range(0, len(src_hoc) - 1, 2):
                startPoint = src_hoc[idx]
                endPoint = src_hoc[idx + 1]
                f.write('{:f}\t{:f}\t{:f} \n'.format(startPoint[0],
                                                     startPoint[1],
                                                     startPoint[2]))
                f.write('{:f}\t{:f}\t{:f} \n'.format(endPoint[0], endPoint[1],
                                                     endPoint[2]))

        with open(egAmFile, 'w') as f:
            for idx in range(0, len(dst_am) - 1, 2):
                startPoint = dst_am[idx]
                endPoint = dst_am[idx + 1]
                f.write('{:f}\t{:f}\t{:f} \n'.format(startPoint[0],
                                                     startPoint[1],
                                                     startPoint[2]))
                f.write('{:f}\t{:f}\t{:f} \n'.format(endPoint[0], endPoint[1],
                                                     endPoint[2]))

        amTrFile = os.path.join(self.outputDirectory, 'amTransformed.txt')
        with open(amTrFile, 'w') as f:
            for it in trAmPoints4D:
                f.write('{:f}\t{:f}\t{:f} \n'.format(it[0], it[1], it[2]))
        return 0

    ### test code below
    def test_something():
        pass

    test_something()
