import os
import re


def hocFile(inputFilePath, outputFilePath, hocPointsWithRad):
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

                if not neuron_section and ((createCommand > -1) and
                                           (soma + apical + dend > -3)):
                    neuron_section = True

                if neuron_section and (line == '\n'):
                    neuron_section = False

                if (pt3daddCommand > -1) and neuron_section:

                    hocPoint = hocPointsWithRad[in_neuron_line_number]

                    line = line.replace("pt3dadd", "")
                    matches = re.findall('-?\d+\.\d?\d+|\-?\d+', line)
                    point = list(map(float, matches))

                    writeHocFile.write(
                        '{{pt3dadd({:f},{:f},{:f},{:f})}}\n'.format(
                            hocPoint[0], hocPoint[1], hocPoint[2], hocPoint[3]))
                    in_neuron_line_number = in_neuron_line_number + 1
                else:
                    writeHocFile.write(line)
    return


def amFileWithRadiusAndUncertainty(inpath, outpath, pointsWithRad,
                                   uncertainties):
    """
    this function will produce amfile with radius and its uncertainties
    To get this function to work provide the input of the original amFile and as an output provide another patt.
    pointsWithRad and uncertainties parameters are also should be arrays.
    """

    with open(inpath) as f:
        data = f.readlines()

    for lv, line in enumerate(data):
        if line.rfind("POINT { float[3] EdgePointCoordinates } @") > -1:
            edge_points_id = int(
                line[line.rfind("POINT { float[3] EdgePointCoordinates } @") +
                     len("POINT { float[3] EdgePointCoordinates } @"):])
            break

    thickness_id = edge_points_id + 1
    uncertainty_id = thickness_id + 1
    rel_uncertainty_id = uncertainty_id + 1

    data = data[:lv + 1] + [
        'POINT { float thickness } @' + str(thickness_id) + '\n'
    ] + data[lv + 1:]
    data = data[:lv + 2] + [
        'POINT { float uncertainty } @' + str(uncertainty_id) + '\n'
    ] + data[lv + 2:]
    data = data[:lv + 3] + [
        'POINT { float rel_uncertainty } @' + str(rel_uncertainty_id) + '\n'
    ] + data[lv + 3:]

    with open(outpath, 'w') as f:

        f.writelines(data)

        f.write('\n')
        f.write('@' + str(thickness_id) + '\n')
        for point in pointsWithRad:
            f.write(str(point[3]) + '\n')

        f.write('\n')
        f.write('@' + str(uncertainty_id) + '\n')
        for e in uncertainties:
            f.write(str(e[0]) + '\n')

        f.write('\n')
        f.write('@' + str(rel_uncertainty_id) + '\n')
        for rel_ucr in uncertainties:
            f.write(str(rel_ucr[1]) + '\n')


def write_spacial_graph_with_error(inpath, outpath, radii):
    """
    This function write the radii of specialGraphFile in the
    outputFIile path provided as parameter.
    """
    with open(inpath) as f:
        data = f.readlines()

    for lv, line in enumerate(data):
        if line.rfind("POINT { float[3] EdgePointCoordinates } @") > -1:
            edge_points_id = int(
                line[line.rfind("POINT { float[3] EdgePointCoordinates } @") +
                     len("POINT { float[3] EdgePointCoordinates } @"):])
            break

    thickness_id = edge_points_id + 1

    data = data[:lv + 1] + [
        'POINT { float thickness } @' + str(thickness_id) + '\n'
    ] + data[lv + 1:]

    with open(outpath, 'w') as f:
        f.writelines(data)
        f.write('\n')
        f.write('@' + str(thickness_id) + '\n')
        for r in radii:
            f.write(str(r) + '\n')


def multipleAmFilesWithRadiusAndUncertainty(inputFolderPath, outputFolderPath,
                                            amFilesWithError):
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

                spacialGraphIndicator = re.findall(r'[sS]\d+',
                                                   specialGraphFile)[0]
                am_file = spacialGraphIndicator + "_with_r" + ".am"

                points = amFilesWithError[str(am_file)]
                pointsWithRad = [point[0:4] for point in points]
                ucrs = [point[4:6] for point in points]

                inputFile = inputFolderPath + str(specialGraphFile)
                outputFile = outputFolderPath + str(specialGraphFile)

                # write_spacial_graph_with_error(inputFile, outputFile, ucr)
                amFileWithRadiusAndUncertainty(inputFile, outputFile,
                                               pointsWithRad, ucrs)
    else:
        inputFile = inputFolderPath
        amFileName = os.path.basename(inputFile)
        outputFile = outputFolderPath + amFileName

        points = amFilesWithError[str(amFileName)]
        pointsWithRad = [point[0:4] for point in points]
        ucrs = [point[4:6] for point in points]

        amFileWithRadiusAndUncertainty(inputFile, outputFile, pointsWithRad,
                                       ucrs)
