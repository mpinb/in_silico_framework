import os
# import cloudpickle
import compatibility
import pandas as pd
from . import parent_classes
import isf_pandas_msgpack


def check(obj):
    '''checks wherther obj can be saved with this dumper'''
    return isinstance(
        obj, (pd.DataFrame,
              pd.Series))  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        #         return pd.read_msgpack(os.path.join(savedir, 'pandas_to_msgpack'))
        path = os.path.join(savedir, 'pandas_to_msgpack')
        if os.path.exists(path):  # 'everything saved in single file'
            return isf_pandas_msgpack.read_msgpack(
                os.path.join(savedir, 'pandas_to_msgpack'))
        else:
            paths = os.listdir(savedir)
            paths = [p for p in paths if 'pandas_to_msgpack' in p]
            paths = sorted(paths, key=lambda x: int(x.split('_')[-1]))
            dfs = [
                isf_pandas_msgpack.read_msgpack(os.path.join(savedir, p))
                for p in paths
            ]
            return pd.concat(dfs)


def dump(obj, savedir, rows_per_file=None):
    '''rows_per_file: automatically splits dataframe, such that rows_per_file rows of the df are
    saved in each file. This helps with large dataframes which otherwise would hit the 1GB limit of msgpack.'''
    #     obj.to_msgpack(os.path.join(savedir, 'pandas_to_msgpack'), compress = 'blosc')
    import os
    if not "ISF_IS_TESTING" in os.environ:
        # Module was not called from within the test suite
        raise RuntimeError(
            'pandas-msgpack is not supported anymore in the model_data_base since Python 3.8')
    import os
    if rows_per_file is not None:
        row = 0
        lv = 0
        while True:
            current_obj = obj.iloc[row:row + rows_per_file]
            row += rows_per_file
            if len(current_obj) == 0:
                break
            print(len(current_obj), lv)
            isf_pandas_msgpack.to_msgpack(os.path.join(
                savedir, 'pandas_to_msgpack_{}'.format(lv)),
                                      current_obj,
                                      compress='blosc')
            lv += 1
    else:
        isf_pandas_msgpack.to_msgpack(os.path.join(savedir, 'pandas_to_msgpack'),
                                  obj,
                                  compress='blosc')


#     with open(os.path.join(savedir, 'Loader.pickle'), 'wb') as file_:
#         cloudpickle.dump(Loader(), file_)
    compatibility.cloudpickle_fun(Loader(),
                                  os.path.join(savedir, 'Loader.pickle'))
