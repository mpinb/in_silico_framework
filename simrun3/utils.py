import Interface as I
import inspect
import six


def get_cellnumbers_from_confile(confile):
    con = I.scp.reader.read_functional_realization_map(confile)
    con = con[0]
    return {k: con[k][-1][1] + 1 for k in list(con.keys())}


def split_network_param_in_one_elem_dicts(dict_):
    out = []
    for k in list(dict_['network'].keys()):
        d = I.defaultdict_defaultdict()
        d['network'][k] = dict_['network'][k]
        out.append(I.scp.NTParameterSet(d))
    return out


def get_default_arguments(func):
    '''Gets the keyword arguments with their default value from any function.
    
    import six
    Returns: dictionary, function names are keys, default values are values'''
    o = inspect.getargspec(func)
    names = o.args[-len(six.get_function_defaults(func)):]
    defaults = o.defaults
    return {n: d for n, d in zip(names, defaults) if d is not None}


def set_default_arguments_if_not_set(o, kwargs):
    '''Used to update attributes of an object based on a dictionary.
    If the attribute is already set, it is NOT opverwritten.
    
    Usecase: If an object has been pickled and the keyword arguments have been extended post hoc, 
    the new keyword arguments are missing. This can be used to update the object accordingly.
    
    import six
    Returns: None'''
    for n, v in six.iteritems(kwargs):
        try:
            getattr(o, n)
        except AttributeError:
            errstr = 'Warning! Setting {} to default value {}'
            print(errstr.format(n, v))
            setattr(o, n, v)