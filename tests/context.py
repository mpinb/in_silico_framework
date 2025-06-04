from __future__ import absolute_import
import os


getting_started_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'getting_started'))

TESTS_CWD = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_FOLDER = os.path.join(
    getting_started_dir, 
    'example_data',
    )
TEST_SIMULATION_DATA_FOLDER = os.path.join(
    getting_started_dir, 
    'example_data',
    'simulation_data',
    'C2_center_example')
assert os.path.exists(TEST_DATA_FOLDER)
assert os.path.exists(TEST_SIMULATION_DATA_FOLDER)

