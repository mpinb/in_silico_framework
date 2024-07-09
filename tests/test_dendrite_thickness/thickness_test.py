"""
This file is used for testing IO.py.
"""
import os
import numpy as np
from dendrite_thickness.thickness import IO, pipeline, utils
from dendrite_thickness.thickness import thickness as th
from .context import CURRENT_DIR 
TEST_DATA_DIR = os.path.join(CURRENT_DIR, 'test_files')
from .context import DATA_DIR as EXAMPLE_DATA_DIR
import six
import logging

logger = logging.getLogger("ISF").getChild(__name__)

AM_FILE = os.path.join(
    EXAMPLE_DATA_DIR, 
    'am_files',
    'S13_final_done_Alison_zScale_40.am')
IMAGE_FILE = os.path.join(
    EXAMPLE_DATA_DIR, 
    'image_files',
    'S13_max_z_projection.tif')


def test_am_read():
    logger.info(AM_FILE)
    logger.info("***********")
    logger.info("TEST Am.read() method:")
    logger.info("***********")

    #   Test 1
    logger.info("TEST 1")
    logger.info("print the test file path:")
    logger.info(AM_FILE)
    logger.info("------")
    am_object = IO.Am(AM_FILE)

    #   Test 2
    logger.info("TEST 2")
    logger.info("am_object:")
    logger.info("output_path: " + am_object.output_path)
    logger.info("input_path: " + am_object.input_path)
    logger.info("-------")

    #  Test 3
    logger.info("TEST 3")
    am_object.read()
    logger.info("commands: ")
    logger.info(am_object.commands)
    logger.info("-------")

    #   Test 4
    logger.info("TEST 4")
    logger.info('profile_data["POINT { float[3] EdgePointCoordinates }"]')
    defined_point = [
        1.849200057983398E01, 5.106000137329102E01, 1.310999989509583E00
    ]
    point = am_object.all_data["POINT { float[3] EdgePointCoordinates }"][3]

    logger.info("The point read from the file is as the same as the one from the " \
          "Am.read() method: " + \
          str(utils.are_same_points(defined_point, point)))
    assert utils.are_same_points(defined_point, point)
    logger.info("-------")

    del am_object


def test_am_write():
    logger.info("***********")
    logger.info("TEST Am.write() method:")
    logger.info("***********")
    am_object = IO.Am(AM_FILE)
    am_object.read()
    am_object.output_path = os.path.join(
        CURRENT_DIR, 
        'test_files', 
        'output',
        'test_write.am')
    if not os.path.exists(am_object.output_path):
        with open(am_object.output_path, "w"):
            pass  # create empty file

    #   Test 1
    am_object.write()


def test_correct_seed():
    """
    Find the nearest brightest point.
    Input is [x, y, original_intensity]
    Output is [new_x, new_y, original_intensity] (for some reason)
    """
    logger.info("***********")
    logger.info("TEST thicknesses._correct_seed() method:")
    logger.info("***********")
    # image point and its value, extracted using ImageJ:
    # x = 2400, y = 2364, value = 149
    # the maximum value in a area of thickness 10 micron is 181 at [2333, 2283]
    image_point = [2400, 2364, 149]  # [x, y, value]
    rx_object = th.ThicknessExtractor([], image_file=IMAGE_FILE)
    corrected_point = rx_object._correct_seed(image_point)
    assert corrected_point == [2333, 2283, 149]
    original_intensity = rx_object.image.GetPixel(
        [int(image_point[0]), int(image_point[1])])
    new_intensity = rx_object.image.GetPixel(
        [int(corrected_point[0]),
         int(corrected_point[1])])
    assert new_intensity > original_intensity


def test_crop_image():
    a = [[1, 2, 3, 4, 5], [2, 3, 4, 5, 6], [3, 4, 5, 6, 7]]
    a = np.array(a)

    # 0 pixels surrounding
    assert th._crop_image(a, (0, 0), 0) == np.array([[1]])

    # 1 pixels surrounding, zero pad the rest
    radius = 1
    a_padded = np.pad(a, radius, 'constant', constant_values=0)
    np.testing.assert_array_almost_equal(
        th._crop_image(a_padded, (0 + radius, 0 + radius), 1),
        np.array([[0, 0, 0], [0, 1, 2], [0, 2, 3]]))
    np.testing.assert_array_almost_equal(
        th._crop_image(a_padded, (0 + radius, 4 + radius), 1),
        np.array([[0, 0, 0], [4, 5, 0], [5, 6, 0]]))
    np.testing.assert_array_almost_equal(
        th._crop_image(a_padded, [1 + radius, 2 + radius], 1, circle=True),
        np.array([[0, 3, 0], [3, 4, 5], [0, 5, 0]]))


def test_pipeline(client):
    am_folder_path = os.path.join(TEST_DATA_DIR, 'am_files')
    tif_folder_path = os.path.join(TEST_DATA_DIR, 'image_files')
    hoc_file_path = os.path.join(TEST_DATA_DIR, '89_L5_CDK20050712_nr6L5B_dend_PC_neuron_transform_registered_C2.hoc')
    output_folder_path = os.path.join(TEST_DATA_DIR, 'output')
    bijective_points_path = os.path.join(TEST_DATA_DIR,'manual_landmarks.landmarkAscii')

    p = pipeline.ExtractThicknessPipeline()

    p.set_am_paths_by_folder(am_folder_path)
    logger.info("set_am_paths_by_folder test, should logger.info the first am file")
    logger.info(p.am_paths[0])

    p.set_tif_paths_by_folder(tif_folder_path)
    logger.info("set_tif_paths_by_folder test, should logger.info the first tif file")
    logger.info(p.tif_paths[0])
    logger.info(os.path.basename(p.am_paths[0]))

    p.set_output_path(output_folder_path)
    logger.info("set_output_path test, should logger.info the output folder path")
    logger.info(p.set_output_path)

    p.set_hoc_file(hoc_file_path)
    logger.info("set_hoc_file test, should logger.info the hoc file path")
    logger.info(p.hoc_file)

    # p.set_thickness_extractor_parameters()
    p.set_am_to_hoc_transformation_by_landmarkAscii(bijective_points_path)
    if six.PY3:  # Only works on Py3?
        p.set_client_for_parallelization(client)
    df = p.run()
