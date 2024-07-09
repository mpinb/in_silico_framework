import os
from getting_started import getting_started_dir

DATA_DIR = os.path.join(
    getting_started_dir,
    'example_data',
    'morphology')
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))