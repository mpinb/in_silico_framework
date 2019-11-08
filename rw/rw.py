import math
import os
import re

import radii as radi
import rw


class Rw:

    """
    The Rw is the superclass for the Rw module.

    parameters
    ----------
    """

    def __init__(self, xyResolution=0.092, zResolution=0.5, xySize=20,
                 numberOfRays=10, tresholdPercentage=0.5, numberOfRaysForPostMeasurment=20):
        self.xyResolution = xyResolution
        self.zResolution = zResolution
        self.xySize = xySize
        self.numberOfRays = numberOfRays
        self.tresholdPercentage = tresholdPercentage

        self.rayLengthPerDirectionOfImageCoordinatesForPostMeasurment = 0.50/xyResolution # self.rayLengthPerDirectionOfImageCoordinates/10
        self.numberOfRaysForPostMeasurment = numberOfRaysForPostMeasurment

        self.radiusCalculator = radi.calcRad.RadiusCalculator(xyResolution=self.xyResolution, zResolution=self.zResolution, xySize=self.xySize, numberOfRays=self.numberOfRays, tresholdPercentage=self.tresholdPercentage)




    def convert_point(self, p, x_res = 0.092, y_res = 0.092, z_res = 1.0):
        out = []
        scaling = [x_res, y_res, z_res]
        for lv, pp in enumerate(p):
            try:
                s = scaling[lv]
            except IndexError:
                s = 2
            out.append(pp*s)
        return out


    def hocFileComplete(self, inputFilePath):
        '''Reading all neuronal points of a hoc file'''
        with open(inputFilePath, 'r') as hocFile:
            lines = hocFile.readlines()
            neuron_section = False
            points = []

            for lineNumber, line in enumerate(lines):
                soma = line.rfind("soma")
                dend = line.rfind("dend")
                apical = line.rfind("apical")
                createCommand = line.rfind("create")
                pt3daddCommand = line.rfind("pt3dadd")

                if not neuron_section and ((createCommand > -1)
                                           and (soma + apical + dend > -3)):
                    neuron_section = True

                if neuron_section and (line == '\n'):
                    neuron_section = False

                if (pt3daddCommand > -1) and neuron_section:
                    line = line.replace("pt3dadd", "")
                    matches = re.findall('-?\d+\.\d?\d+|\-?\d+', line)
                    point = map(float, matches)
                    points.append(point)
        return points


    def hocFileReduced(self, inputFilePath):
        """
        Reading hoc file with only two points (top and bottom) from each section of
        neuronal points of a hoc file

        """
        with open(inputFilePath, 'r') as hocFile:
            lines = hocFile.readlines()
            neuron_section = False
            points = []
            lastPoint = []

            in_neuron_line_number = 0

            for lineNumber, line in enumerate(lines):
                # raw_input("Press Enter to continue...")
                soma = line.rfind("soma")
                dend = line.rfind("dend")
                apical = line.rfind("apical")
                createCommand = line.rfind("create")
                pt3daddCommand = line.rfind("pt3dadd")
                # print("line:")
                # print(lineNumber)
                # print("the content:")
                # print(line)
                if not neuron_section and ((createCommand > -1)
                                           and (soma + apical + dend > -3)):
                    neuron_section = True
                    # print("in_neuron True")

                if neuron_section and (line == '\n'):
                    neuron_section = False
                    in_neuron_line_number = 0
                    points.append(lastPoint)
                    lastPoint = []
                    # print("in_neuron True and line empty")

                if (pt3daddCommand > -1) and neuron_section:
                    in_neuron_line_number = in_neuron_line_number + 1;
                    line = line.replace("pt3dadd", "")
                    matches = re.findall('-?\d+\.\d?\d+|\-?\d+', line)
                    point = map(float, matches)
                    # print("in p3dadd command")
                    if (in_neuron_line_number == 1):
                        points.append(point)
                    else:
                        lastPoint = point
        return points


    def amFile(self, inputFilePath):
        """
        Reading all points of am file with also their radius form the
        thickness part of the file

        """
        with open(inputFilePath, 'r') as amFile:
            lines = amFile.readlines()
            points = []
            rads = []
            pointsWithRad = []
            in_edge_section = False
            in_thickness_section = False

            for l_number, l in enumerate(lines):
                line_thickness = l.rfind("float thickness")
                line_edge = l.rfind("float[3] EdgePointCoordinates")
                char_idx = 0
                if line_thickness > -1:
                    char_idx = l.rfind("@")
                    thickness_sign_number = l[char_idx + 1]
                    thickness_sign = "@"+ thickness_sign_number

                elif (line_edge > -1):
                    char_idx = l.rfind("@")
                    edge_sign_number = l[char_idx + 1 ]
                    edge_sign = "@"+ edge_sign_number

            for lineNumber, line in enumerate(lines):

                edge_sign_presense = line.rfind(edge_sign)
                EdgePointCoordinates = line.rfind("EdgePointCoordinates")

                thickness_sign_presense = line.rfind(thickness_sign)
                thickness = line.rfind("thickness")

                if edge_sign_presense > -1 and EdgePointCoordinates < 0:
                    in_edge_section = True
                    continue

                if thickness_sign_presense > -1 and thickness < 0:
                    in_thickness_section = True
                    continue

                if in_edge_section and (line != '\n'):
                    # please test if their results are compatible or not
                    # matches = re.findall('-?\d+\.\d+e[+-]?\d+', line)
                    matches = re.findall('-?\d+\.\d+[e]?[+-]?\d+', line)
                    point = map(float, matches)
                    points.append(point)

                if in_edge_section and (line == '\n'):
                    in_edge_section = False

                if in_thickness_section and (line != '\n'):
                    # please test if their results are compatible or not
                    # matches = re.findall('-?\d+\.\d+e[+-]?\d+', line)
                    matches = re.findall('-?\d+\.\d+[e]?[+-]?\d+', line)
                    if matches == []:
                        matches = [0.0,0.0]
                    rad = map(float, matches)
                    rads.append(rad)

                if in_thickness_section and (line == '\n'):
                    in_thickness_section = False

            for idx, point in enumerate(points):
                pointsWithRad.append([point[0], point[1], point[2], rads[idx][0]])

        return pointsWithRad


    def multipleAmFiles(self, inputFolderPath):

        """
        Input a folder path which contains the am files
        Output the am files with radius as a dictionary of am files paths
        and a full array of all points with their radii
        """

        oneAmFilePoints =[]
        allAmPoints = []
        amFilesSet = {}

        for am_file in os.listdir(inputFolderPath):
            oneAmFilePoints =[]
            if am_file.endswith(".am"):
                pathToAmFile = inputFolderPath + str(am_file)
                oneAmFilePoints = amFile(pathToAmFile)
                amFilesSet[str(am_file)] = oneAmFilePoints
                allAmPoints = allAmPoints + oneAmFilePoints
        return allAmPoints, amFilesSet


    def getSpatialGraphPoints(self, spatial_graph):
        """
        #input: path of the data.
        #output: pints in an array
        """

        with open(spatial_graph, 'r') as csb:
            edge_ids = []
            edge_num_points = []
            edge_point_coords = []

            looking_for_axon_id = False
            looking_for_dend_id = False
            looking_for_soma_id = False
            looking_for_num_edge_points = False
            looking_for_edge_labels = False
            looking_for_edge_coords = False

            axon_id = 0
            dend_id = 0
            soma_id = 0
            edge_num_points_id = 0
            edge_ids_id = 0
            edge_points_id = 0

            lines = csb.readlines()

            # for each manual landmark
            for lv, line in enumerate(lines):

                if line.rfind("EDGE { int NumEdgePoints } @")>-1:
                    edge_num_points_id = int(line[line.rfind("EDGE { int NumEdgePoints } @")+len("EDGE { int NumEdgePoints } @"):])
                    #print 'edge_num_points_id', edge_num_points_id

                if line.rfind("EDGE { int EdgeLabels } @")>-1:
                    edge_ids_id = int(line[line.rfind("EDGE { int EdgeLabels } @")+len("EDGE { int EdgeLabels } @"):])
                    #print 'edge_ids_id', edge_ids_id

                if line.rfind("POINT { float[3] EdgePointCoordinates } @")>-1:
                    edge_points_id = int(line[line.rfind("POINT { float[3] EdgePointCoordinates } @")+len("POINT { float[3] EdgePointCoordinates } @"):])
                    #print 'edge_points_id', edge_points_id

                if line.find("@{}".format(edge_num_points_id)) == 0:
                    looking_for_num_edge_points = True
                    #print "found {}".format(edge_num_points_id)
                    continue
                if looking_for_num_edge_points :
                    if (line.rfind("@") == 0 or line.isspace()):
                        looking_for_num_edge_points = False
                        continue
                    else:
                        edge_num_points.append( int(line ))

                if line.find("@{}".format(edge_ids_id)) == 0:
                    looking_for_edge_labels = True
                    #print "found {}".format(edge_ids_id)
                    continue
                if looking_for_edge_labels :
                    if (line.rfind("@") == 0 or line.isspace()):
                        looking_for_edge_labels = False
                        continue
                    else:
                        edge_ids.append( int(line ))

                if line.find("@{}".format(edge_points_id)) == 0:
                    looking_for_edge_coords = True
                    #print lv
                    #print "found {}".format(edge_points_id)
                    continue
                if looking_for_edge_coords :
                    if (line.rfind("@") == 0 or line.isspace()):
                        looking_for_edge_coords = False
                        continue
                    else:
                        edge_point_coords.append( list(map(float,line.split())))
                        #edge_point_coords.append( float(line.split()))

        return edge_point_coords


    def write_spacial_graph_with_thickness(self, inpath, outpath, radii):
        '''by arco'''
        with open(inpath) as f:
            data = f.readlines()

        for lv, line in enumerate(data):
            if line.rfind("POINT { float[3] EdgePointCoordinates } @")>-1:
                edge_points_id = int(line[line.rfind("POINT { float[3] EdgePointCoordinates } @")+len("POINT { float[3] EdgePointCoordinates } @"):])
                break

        thickness_id = edge_points_id + 1

        data = data[:lv+1] + ['POINT { float thickness } @' + str(thickness_id) + '\n'] + data[lv+1:]

        with open(outpath, 'w') as f:
            f.writelines(data)
            f.write('\n')
            f.write('@'+str(thickness_id) + '\n')
            for r in radii:
                if math.isnan(r):
                    f.write(str(0.0)+'\n')
                else:
                    f.write(str(r)+'\n')


    def hocFile(self, inputFilePath, outputFilePath, hocPointsWithRad):
        """
        # Writing points with their radius to a specific hoc file.
        # basically it do this: reading a file without the
        # radii of neuronal points and add the radius to them in another hoc file
        """


        with open(inputFilePath, 'r') as readHocFile:
            with open(outputFilePath, 'w') as writeHocFile:
                lines = readHocFile.readlines()
                neuron_section = False

                in_neuron_line_number = 0

                for lineNumber, line in enumerate(lines):
                    soma = line.rfind("soma")
                    dend = line.rfind("dend")
                    apical = line.rfind("apical")
                    createCommand = line.rfind("create")
                    pt3daddCommand = line.rfind("pt3dadd")

                    if not neuron_section and ((createCommand > -1)
                                            and (soma + apical + dend > -3)):
                        neuron_section = True

                    if neuron_section and (line == '\n'):
                        neuron_section = False

                    if (pt3daddCommand > -1) and neuron_section:

                        hocPoint = hocPointsWithRad[in_neuron_line_number]

                        line = line.replace("pt3dadd", "")
                        matches = re.findall('-?\d+\.\d?\d+|\-?\d+', line)
                        point = map(float, matches)

                        writeHocFile.write('{{pt3dadd({:f},{:f},{:f},{:f})}}\n'.format(hocPoint[0],
                                                                        hocPoint[1],
                                                                        hocPoint[2],
                                                                        hocPoint[3]))
                        in_neuron_line_number = in_neuron_line_number + 1;
                    else:
                        writeHocFile.write(line)
        return


    def amFileWithRadiusAndUncertainty(self, inpath, outpath, pointsWithRad, uncertainties):
        """
        this function will produce amfile with radius and its uncertainties
        To get this function to work provide the input of the original amFile and as an output provide another patt.
        pointsWithRad and uncertainties parameters are also should be arrays.
        """

        with open(inpath) as f:
            data = f.readlines()

        for lv, line in enumerate(data):
            if line.rfind("POINT { float[3] EdgePointCoordinates } @")>-1:
                edge_points_id = int(line[line.rfind("POINT { float[3] EdgePointCoordinates } @")+len("POINT { float[3] EdgePointCoordinates } @"):])
                break

        thickness_id = edge_points_id + 1
        uncertainty_id = thickness_id + 1
        rel_uncertainty_id = uncertainty_id + 1

        data = data[:lv+1] + ['POINT { float thickness } @' + str(thickness_id) + '\n'] + data[lv+1:]
        data = data[:lv+2] + ['POINT { float uncertainty } @' + str(uncertainty_id) + '\n'] + data[lv+2:]
        data = data[:lv+3] + ['POINT { float rel_uncertainty } @' + str(rel_uncertainty_id) + '\n'] + data[lv+3:]

        with open(outpath, 'w') as f:

            f.writelines(data)

            f.write('\n')
            f.write('@'+str(thickness_id) + '\n')
            for point in pointsWithRad:
                f.write(str(point[3])+'\n')

            f.write('\n')
            f.write('@'+str(uncertainty_id) + '\n')
            for e in uncertainties:
                f.write(str(e[0])+'\n')

            f.write('\n')
            f.write('@'+str(rel_uncertainty_id) + '\n')
            for rel_ucr in uncertainties  :
                f.write(str(rel_ucr[1])+'\n')


    def write_spacial_graph_with_error(inpath, outpath, radii):
        """
        This function write the radii of specialGraphFile in the
        outputFIile path provided as parameter.
        """
        with open(inpath) as f:
            data = f.readlines()

        for lv, line in enumerate(data):
            if line.rfind("POINT { float[3] EdgePointCoordinates } @")>-1:
                edge_points_id = int(line[line.rfind("POINT { float[3] EdgePointCoordinates } @")+len("POINT { float[3] EdgePointCoordinates } @"):])
                break

        thickness_id = edge_points_id + 1

        data = data[:lv+1] + ['POINT { float thickness } @' + str(thickness_id) + '\n'] + data[lv+1:]

        with open(outpath, 'w') as f:
            f.writelines(data)
            f.write('\n')
            f.write('@'+str(thickness_id) + '\n')
            for r in radii:
                f.write(str(r)+'\n')


    def multipleAmFilesWithRadiusAndUncertainty(self, inputFolderPath, outputFolderPath, amFilesWithError):

        """
        write the pints with their radii and uncertainties for bunch of amfiles.
        if you want to only write one amFile you can use write_spacial_graph_with_error() function.

        """
        points = []
        ucr = []
        pointsWithRad = []
        if os.path.isdir(inputFolderPath):
            for specialGraphFile in os.listdir(inputFolderPath):
                if specialGraphFile.endswith(".am"):

                    spacialGraphIndicator = re.findall(r'[sS]\d+', specialGraphFile)[0]
                    am_file = spacialGraphIndicator + "_with_r" + ".am"

                    points = amFilesWithError[str(am_file)]
                    pointsWithRad = [point[0:4] for point in points]
                    ucrs = [point[4:6] for point in points]

                    inputFile = inputFolderPath + str(specialGraphFile)
                    outputFile = outputFolderPath + str(specialGraphFile)

                    # write_spacial_graph_with_error(inputFile, outputFile, ucr)
                    amFileWithRadiusAndUncertainty(inputFile, outputFile, pointsWithRad, ucrs)
        else:
            inputFile = inputFolderPath
            amFileName = os.path.basename(inputFile)
            outputFile = outputFolderPath + amFileName

            points = amFilesWithError[str(amFileName)]
            pointsWithRad = [point[0:4] for point in points]
            ucrs = [point[4:6] for point in points]

            amFileWithRadiusAndUncertainty(inputFile, outputFile, pointsWithRad, ucrs)



    def exRadSets(self, path_to_am, path_to_tif, path_to_output_folder, postMeasurment='no'):
        """
            This method extracts all of the radii sets, each set corresponds to an
            .am file, and writes the calculated radii in new .am files in a new folder.

    Inputs:
    path_to_am: path to the folder contains the initial .am files without radius.
    path_to_tif: path to the folder contains the tif images corresponds to .am
    files.
    path_to_output: path to the output folder and its name.

    Outputs:
    1. calculats radii sets, and puts each set inside its corresponding .am file
    inside the given output folder path.
        extraxt radii sets of bunch of files from the folder of path_to_am
        and writ them to and output folder
        """

        if (os.path.isdir(path_to_am) and os.path.isdir(path_to_tif)):
            for spacialGraphFile in os.listdir(path_to_am):
                if spacialGraphFile.endswith(".am"):
                    points = self.readPoints(path_to_am + spacialGraphFile)
                    if points == "error": continue
                    spacialGraphIndicator = re.findall(r'[sS]\d+', spacialGraphFile)[0]
                    outputFile = path_to_output_folder + spacialGraphIndicator + \
                        "_with_r" + ".am"
                    for imageFile in os.listdir(path_to_tif):
                        if imageFile.startswith(spacialGraphIndicator):
                            image = self.readImage(path_to_tif + imageFile)
                            # result = radi.radius.getRadiiHalfMax(image, points)
                            result = self.radiusCalculator.getProfileOfThesePoints(image, points, postMeasurment)
                            print(imageFile)
                            self.writeResult(path_to_am + spacialGraphFile, outputFile, result)
                            break
        else:
            points = self.readPoints(path_to_am)
            if points == "error": return "error"
            amFileName = os.path.basename(path_to_am)
            outputFile = path_to_output_folder + "/" + amFileName
            imageFile = path_to_tif
            image = self.readImage(imageFile)
            result = self.radiusCalculator.getProfileOfThesePoints(image, points, postMeasurment)
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
            points = rw.getSpatialGraphPoints(dataFile)
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
        points = map(lambda x: rw.convert_point(x, 1.0 / 0.092, 1.0 / 0.092, 1.0), points)

        return points

    def writeResult(self, inputDataFile, outputDataFile, result):
        '''This function will write the result of the extracted radii to final am file '''
        radii = result
        radii = [r*0.092 for r in radii]
        try:
            rw.write_spacial_graph_with_thickness(inputDataFile, outputDataFile, radii)
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