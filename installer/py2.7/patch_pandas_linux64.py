# NOTE: activate the conda environment before running this script.
# patch pandas
# this adds support for CategoricalIndex for msgpack format
# by arco, 2018-08-30
import os
import pandas.io.packers

print('patching pandas to support CategoricalIndex in msgpack format')

basedir = os.path.dirname(__file__)
dest_path = os.path.dirname(pandas.io.packers.__file__)
dest_path = os.path.join(dest_path, 'packers.py')
source_path = os.path.join(basedir, 'pandas_patch', 'packers.py')
with open(dest_path, 'w') as f_dest:
    with open(source_path) as f_source:
        f_dest.write(f_source.read())
