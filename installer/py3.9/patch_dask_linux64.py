# NOTE: activate the conda isf-py3 environment before running the script.

import os

basedir = os.path.dirname(__file__)  # sys.argv[0]

# patch dask
import dask, shutil

patches_dir = os.path.join(basedir, "dask_patch")
dask_dir = os.path.dirname(dask.__file__)
files = ["config.py", "base.py"]
for file_ in files:
    shutil.copy(os.path.join(patches_dir, file_), os.path.join(dask_dir, file_))
