import pandas as pd
import numpy as np


def map_return_to_series(fun, *args, **kwargs):

    def inner(*args, **kwargs):
        dummy = fun(*args, **kwargs)
        return pd.Series(dict(A=dummy))

    return inner


def is_int(x):
    '''checks an object is int. surpringingly fast.'''
    try:
        int(x)
        return True
    except:
        return False


def time_list_from_pd(syn):
    '''returns the columns, that can be interpreted as integer:
    'name1' 'nam2' '3' '1' '2' --> '3' '1' '2' 
    The underlying assupmtion is, that the dataframe syn consists
    of columsn like 'name', 'color', 'bla', which describe the data
    and columns like '1', '2', '3', which are the actual data.'''
    relevant_columns = [_ for _ in syn if is_int(_)]
    out = []
    for col in relevant_columns:
        dummy = syn[col]
        dummy = dummy.dropna()
        out.append(dummy)
    return pd.concat(out).values


#def time_list_from_pd(pdf):
#    '''returns all values in columns that can be converted to int without NaN'''
#    relevant_columns = [_ for _ in pdf if is_int(_)]
#    return pd.Series(pdf[relevant_columns].values.flatten()).dropna().values


#pd_to_array = np.asarray
def pd_to_array(pdf):
    try:
        return pdf.to_numpy()
    except AttributeError:
        print('asd')
        return pdf.values  # legacy version of pandas used in in_silico_framework 2, but now deprecated


#def pd_to_array(x):
#    '''converts pd dataframe to array.
#    not very efficient ... use for small dataframes only.'''
#    if x.empty:
#        return np.array([])
#    #x = pdframe.copy()
#    array = []
#    for lv in range(max(x.index.values)+1):
#        if lv in list(x.index.values):
#            array.append(x.loc[lv])
#        else:
#            array.append([0]*len(x.iloc[0]))
#    return np.array(array)
#pdf = pd.DataFrame(np.random.random(size=(1000,1000)))
#I.np.testing.assert_equal(np.asarray(pdf),pd_to_array(pdf))