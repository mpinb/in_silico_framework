import datetime
from functools import partial
import Interface as I
from data_base.exceptions import DataBaseException
import six


class Explore(list):
    '''Use this class to specify a parameterrange to be explored'''
    pass


class Dependency():
    '''Use this class to specify dependencies in the parameterspace'''

    def __init__(self):
        self._dicts = []
        self._values = []
        self._keys = None

    import six

    @staticmethod
    def _flatten_dict(dict_):
        return {
            (k1, k2): v for k1 in list(dict_.keys())
            for k2, v in six.iteritems(dict_[k1])
        }

    def add(self, value, dict_):
        dict_ = self._flatten_dict(dict_)
        keys = sorted(dict_.keys())
        if self._keys is None:
            self._keys = keys
        else:
            if not self._keys == keys:
                errstr = 'Once keys are set, you cannot change them! \nShould be:{}\nIs:{}'
                raise ValueError(errstr.format(self._keys, keys))
        if dict_ in self._dicts:
            errstr = 'parameters already set!'
            raise ValueError(errstr)
        self._dicts.append(dict_)
        self._values.append(value)

    import six

    def resolve(self, parameters):
        parameters = self._flatten_dict(parameters)
        parameters = {
            k: v for k, v in six.iteritems(parameters) if k in self._keys
        }
        if not list(parameters.keys()) == self._keys:
            errstr = 'Cannot resolve {} as it does not match the specified parameters which are {}'
            raise ValueError(errstr.format(list(parameters.keys()), self._keys))
        return self._values[self._dicts.index(parameters)]


d = Dependency()
d.add(1, dict(name1=dict(par1=5, par2=1)))
d.add(2, dict(name1=dict(par1=6, par2=2)))
d.add(3, dict(name1=dict(par1=5, par2=3)))
d.add(4, dict(name1=dict(par1=6, par2=4)))
assert d.resolve({'name1': {'par1': 5, 'par2': 1}}) == 1
assert d.resolve({'name1': {'par1': 6, 'par2': 2}}) == 2
assert d.resolve({'name1': {'par1': 5, 'par2': 3}}) == 3
assert d.resolve({'name1': {'par1': 6, 'par2': 4}}) == 4
try:
    d.resolve({'name1': {'par1': 5, 'par2': 2}})
except:
    pass
else:
    raise RuntimeError("This must raise an exception!")
try:
    d.resolve({'name1': {'par1': 5}})
except:
    pass
else:
    raise RuntimeError("This must raise an exception!")

import itertools


class SimulationFlow:

    def __init__(self,
                 db,
                 name,
                 cell_params_dict=None,
                 network_params_dict=None,
                 autosetup=True):
        self.network_params = network_params_dict
        self.cell_params = cell_params_dict
        self.name = name
        self.db = db
        self._db = [
        ]  # contains parameters, i.e. the **kwargs of the register function
        self._funtype = [
        ]  # either 'cell' or 'network' depending on what is modified
        self._fun = [
        ]  # fun to be applied. not unique as you could use the same function with different parameters twice
        self._name = [
        ]  # unique. assigned by the user to describe the manipulation.
        self._explored_parameters = [
        ]  # lists parameters for which a space is defined using the Explore class

        self._relative_paths = None
        self._futures_simulation = None
        self._delayeds_simulation = None
        self._futures_paramfiles = None
        self._delayeds_paramfiles = None
        self._cell_param_templates = None
        self._network_param_templates = None
        self._final_param_files = None

        if not len(list(db.keys())) == 0:
            print('Warning! db not empty!')

        if autosetup:
            self._save_template_parameterfiles()
            self.register('cell',
                          cell_param_modify_fun=partial(
                              _get_cell_params, self._cell_param_templates),
                          id_=Explore(list(self.cell_params.keys())))
            self.register(
                'network',
                network_param_modify_fun=partial(
                    _get_network_params,
                    self._network_param_templates),  #self._get_network_params, 
                loc=Explore(list(self.network_params.keys())))

    import six

    def _save_template_parameterfiles(self, verbose=True):
        try:
            outdir = self.db.create_managed_folder('cell_param_templates',
                                                    raise_=True)
            for k, v in six.iteritems(self.cell_params):
                v.save(outdir.join(k))
        except DataBaseException:
            if verbose:
                print('cell_param_templates already saved. skipping.')
        try:
            outdir = self.db.create_managed_folder('network_param_templates',
                                                    raise_=True)
            for k, v in six.iteritems(self.network_params):
                v.save(outdir.join(k))
        except DataBaseException:
            if verbose:
                print('network_param_templates already saved. skipping.')
        try:
            params_outdir = self.db.create_managed_folder('final_param_files',
                                                           raise_=True)
            with open(params_outdir.join('hierarchy.txt'), 'w') as f:
                f.write(self.get_description())
        except DataBaseException:
            if verbose:
                print('final_param_files folder already created. skipping.')
            # replace network_param structures with path
        self._cell_param_templates = self.db['cell_param_templates']
        self._network_param_templates = self.db['network_param_templates']
        self._final_param_files = self.db['final_param_files']
        self.cell_params = {
            k: self._cell_param_templates.join(k) for k in self.cell_params
        }
        self.network_params = {
            k: self._network_param_templates.join(k) for k in self.network_params
        }

    def register(self,
                 name,
                 cell_param_modify_fun=None,
                 network_param_modify_fun=None,
                 **kwargs):
        if not ((cell_param_modify_fun is None) != (network_param_modify_fun
                                                    is None)):
            raise ValueError(
                'You must specify EITHER cell_param_modify_fun OR network_param_modify_fun.'
            )
        if name in self._name:
            raise ValueError('name must be unique!')
        if cell_param_modify_fun is not None:
            self._funtype.append('cell')
            funname = cell_param_modify_fun
            self._fun.append(cell_param_modify_fun)
        elif network_param_modify_fun is not None:
            self._funtype.append('network')
            funname = network_param_modify_fun
            self._fun.append(network_param_modify_fun)

        self._db.append(kwargs)
        self._name.append(name)

    def _step1_prepare_product(self):
        i = []
        l = []
        for name, kwargs in zip(self._name, self._db):
            for pname in sorted(kwargs.keys()):
                p = kwargs[pname]
                i.append((name, pname))
                if isinstance(p, Explore):
                    l.append(p)
                    self._explored_parameters.append(name)
                else:
                    l.append((p,))
        return i, l

    def _step2_evaluate_product(self):
        out_list = []
        i, ll = self._step1_prepare_product()
        for l in itertools.product(*ll):
            out = I.defaultdict(dict)
            for (i1_, i2_), l_ in zip(i, l):
                out[i1_][i2_] = l_
            out_list.append(dict(out))
        return out_list

    import six

    def _step3_resolve_dependencies(self):
        out_list = self._step2_evaluate_product()
        for d in out_list:
            for k1, d1 in six.iteritems(d):
                for k2, v in six.iteritems(d1):
                    if isinstance(v, Dependency):
                        d1[k2] = v.resolve(d)
        return out_list

    def _get_param_name_string(self, params):
        out = []
        for p in self._name:
            v = params[p]
            if not p in self._explored_parameters:
                continue
            _ = '__'.join('{}'.format(v[pp]) for pp in sorted(v.keys()))
            out.append(_)
        return '/'.join(out)

    def get_description(self):
        params = self._step3_resolve_dependencies()
        len_ = len(params)
        param = self._step3_resolve_dependencies()[0]
        out = []
        for p in self._name:
            v = param[p]
            if not p in self._explored_parameters:
                continue
            _ = '{}__'.format(p)
            _ += '__'.join('{}'.format(pp) for pp in sorted(v.keys()))
            out.append(_)
        hierarchy = '/'.join(out)
        example = self._get_param_name_string(param)
        outstr = 'Creating parameterfiles for {} scenarios.\n'.format(len_)
        outstr += 'The hierarchy of the folder structure is: {}\n'.format(
            hierarchy)
        outstr += 'Example: {}\n'.format(example)
        return outstr  # number of parameters, hierarchy, example

    def create_parameterfiles(self, client):
        print(self.get_description())
        self._set_relative_paths()

        self._save_template_parameterfiles()
        parameters = self._step3_resolve_dependencies()
        self._delayeds_paramfiles = [
            _execute_parameterfile_creation(p, self._name, self._fun,
                                            self._funtype,
                                            self._final_param_files,
                                            self._get_param_name_string(p))
            for p in parameters
        ]
        self._futures_paramfiles = client.compute(self._delayeds_paramfiles)

    def _set_relative_paths(self):
        parameters = self._step3_resolve_dependencies()
        self._relative_paths = [
            self._get_param_name_string(p) for p in parameters
        ]

    def run_simulation(self,
                       client,
                       nSweeps=1,
                       nprocs=10,
                       silent=False,
                       tStop=345,
                       dryrun=False):
        I.distributed.wait(self._futures_paramfiles)
        self._set_relative_paths()
        for p in self._relative_paths:
            assert I.os.path.exists(
                self._final_param_files.join(p).join('cell.param'))
            assert I.os.path.exists(
                self._final_param_files.join(p).join('network.param'))
        if 'simrun' in list(self.db.keys()):
            print('Warning! The simrun folder is not empty!')
        outdir = self.db.create_managed_folder('simrun', raise_=False)
        self._delayeds_simulation = []
        for p in self._relative_paths:
            d = I.simrun_run_new_simulations(
                self._final_param_files.join(p).join('cell.param'),
                self._final_param_files.join(p).join('network.param'),
                dirPrefix=outdir.join(p),
                nSweeps=nSweeps,
                nprocs=nprocs,
                scale_apical=None,
                silent=silent,
                tStop=tStop)
            self._delayeds_simulation.append(d)
        if not dryrun:
            self._futures_simulation = client.compute(self._delayeds_simulation)

    def db_init(self, client, mode='full'):
        if not mode in ('full', 'full_delete', 'spike_times'):
            raise ValueError(
                "mode must be one of ('full', 'full_delete', 'spike_times')")
        I.distributed.wait(self._futures_simulation)
        if 'full' in mode:
            I.db_init_simrun_general.init(self.db,
                                           self.db['simrun'],
                                           client=client)
        if 'spike_times' in mode:
            I.db_init_simrun_general.init(self.db,
                                           self.db['simrun'],
                                           client=client,
                                           synapse_activation=False,
                                           dendritic_voltage_traces=False,
                                           core=True,
                                           parameterfiles=False,
                                           spike_times=True,
                                           burst_times=False,
                                           repartition=False)
        if 'delete' in mode:
            del self.db['simrun']

    def run_all_remote(self,
                       client,
                       mode='full',
                       nSweeps=1,
                       nprocs=10,
                       silent=False,
                       tStop=345):

        def helper():
            I.distributed.secede()
            c = I.distributed.get_client(timeout=300)
            self.create_parameterfiles(c)
            self.run_simulation(c, nSweeps, nprocs, silent, tStop)
            self.db_init(c, mode)
            return self

        print(self.get_description())
        self._future_run_all_remote = client.submit(helper)


### outside of class as there were deserialization issues


def _get_cell_params(_cell_param_templates, irrelevant, id_=None):
    return I.scp.build_parameters(_cell_param_templates.join(id_))


def _get_network_params(_network_param_templates, irrelevant, loc=None):
    return I.scp.build_parameters(_network_param_templates.join(loc))


@I.dask.delayed
def _execute_parameterfile_creation(parameters,
                                    _name=None,
                                    _fun=None,
                                    _funtype=None,
                                    _final_param_files=None,
                                    relative_outdir=None):

    def apply_fun(name, fun, param, kwargs):
        print(name)
        if param is None:
            raise ValueError(
                'Did not receive param structure! Cannot apply {} with parameters {}.'
                .format(name, kwargs))
        param_bak = param.as_dict()
        param = fun(param, **kwargs)
        if param_bak == param.as_dict():
            errstr = 'Warning! Applied {} but nothing changed!'
            errstr = errstr.format(name)
            I.warnings.warn(errstr)
        return param

    cell_param = I.scp.NTParameterSet({})
    network_param = I.scp.NTParameterSet({})
    for name, fun, funtype in zip(_name, _fun, _funtype):
        p = parameters[name]
        if funtype == 'cell':
            cell_param = apply_fun(name, fun, cell_param, p)
        elif funtype == 'network':
            network_param = apply_fun(name, fun, network_param, p)
        else:
            raise RuntimeError("This should not have happend!!!")

    # if not 'info' in cell_param:
    #     cell_param['info'] = I.scp.NTParameterSet({})
    # if not 'info' in network_param:
    #     network_param['info'] = I.scp.NTParameterSet({})
    # network_param.info['date'] = cell_param.info['date'] = datetime.datetime.today().strftime('%d%b%Y')
    # network_param.info['note'] = cell_param.info['note'] = "This parameterfile has been generated with the simulation_flow module. "
    # network_param.info['versionid'] = cell_param.info['versionid'] = "VersionID: {} ".format(I.get_versions()['version'])
    # network_param.info['simulation_parameters'] = cell_param.info['simulation_parameters'] = "{}".format(parameters)
    outdir = _final_param_files.join(relative_outdir)
    if not I.os.path.exists(outdir):
        I.os.makedirs(outdir)
    cell_param.save(outdir.join('cell.param'))
    network_param.save(outdir.join('network.param'))
    # raise ValueError(outdir)
    return relative_outdir


# s = SimulationFlow({}, 'test', {'m1': 1, 'm2':2}, {'n1': 1, 'n2':2})
# d = Dependency()
# d.add('syn_strength_1', {'cell':{'id_': 'm1'}})
# d.add('syn_strength_2', {'cell':{'id_': 'm2'}})
# s.register('modify_syn_strength', network_param_modify_fun = 'asd', syn_strength = d)
# out = s._step3_resolve_dependencies()
# out_expected = [{'cell': {'id_': 'm1'},
#   'modify_syn_strength': {'syn_strength': 'syn_strength_1'},
#   'network': {'loc': 'n1'}},
#  {'cell': {'id_': 'm1'},
#   'modify_syn_strength': {'syn_strength': 'syn_strength_1'},
#   'network': {'loc': 'n2'}},
#  {'cell': {'id_': 'm2'},
#   'modify_syn_strength': {'syn_strength': 'syn_strength_2'},
#   'network': {'loc': 'n1'}},
#  {'cell': {'id_': 'm2'},
#   'modify_syn_strength': {'syn_strength': 'syn_strength_2'},
#   'network': {'loc': 'n2'}}]
# assert out == out_expected