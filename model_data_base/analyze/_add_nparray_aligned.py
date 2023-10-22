import numpy as np


def max_array_dimensions(*args):
    '''takes numpy arrays and returnes the maximal dimensions'''
    for x in args:
        if not isinstance(x, np.ndarray):
            raise RuntimeError("wrong input type. Expect numpy.array, got %s" %
                               str(type(x)))

    #ignore empty arrays
    args = [a for a in args if len(a.shape) == 2]
    list_size = list(map(np.shape, args))
    list_size = list(zip(*list_size))
    list_size = list(map(max, list_size))
    return list_size


def add_aligned(*args):
    '''takes numpy arrays, which may have different sizes and adds them in the following way:
    All arrays are aligned to the top left corner. Then they are expanded, until they are
    as big as the biggest array. Then they are added.'''
    maxSize = max_array_dimensions(*args)  #includes typechecking
    out = np.zeros(maxSize)
    for x in args:
        #ignore empty arrays
        if not len(x.shape) == 2:
            continue
        y = x.copy()
        y = np.concatenate((y, np.zeros([maxSize[0] - y.shape[0], y.shape[1]])),
                           axis=0)
        y = np.concatenate((y, np.zeros([y.shape[0], maxSize[1] - y.shape[1]])),
                           axis=1)
        out = out + y

    return out
