'''
This module implements a framework to 

What should I do if
 - I run my reduced model but the strategies are not executed remotely?
     --> make sure, the strategy has a Solver registered
'''

import Interface as I
import sklearn.metrics
import scipy.optimize
import numpy
try:
    import cupy
    import cupy as np
    CUPY_ENABLED = True
except ImportError:
    import numpy as np
    print('CuPy could not be imported.')
    CUPY_ENABLED = False

import pandas as pd
import matplotlib.pyplot as plt
import weakref


def convert_to_numpy(x):
    if CUPY_ENABLED:
        return cupy.asnumpy(x)
    else:
        return x


# cupy frees GPU memory when all references are deleted
# as this is difficult to track, use the make_weakref method, which stores all
# GPU arrays in the _WEAKREF_ARRAY_LIST and returns a weakref object. This can be used to
# interact with the data, but is not a reference.
# Therefore, it is sufficient to empty _WEAKREF_ARRAY_LIST, which frees the GPU memory.
# All weakref objects pointing to GPU arrays will then be invalidated.
_WEAKREF_ARRAY_LIST = []


def make_weakref(obj):
    _WEAKREF_ARRAY_LIST.append(obj)
    return weakref.proxy(obj)


def clear_memory():
    del _WEAKREF_ARRAY_LIST[:]


def dereference(weakrefobj):
    '''Dereferences a weakref.proxy object, returning a reference to the underlying object itself.
    Uses private interface ... check after version update!
    https://stackoverflow.com/questions/19621036/acquiring-a-regular-reference-from-a-weakref-proxy-in-python'''
    return weakrefobj.__repr__.__self__


def get_n_workers_per_ip(workers, n):
    '''helper function to get n workers per machine'''
    s = I.pd.Series(workers)
    return s.groupby(s.str.split(':').str[1]).apply(lambda x: x[:n]).tolist()


class Rm(object):

    def __init__(self,
                 name,
                 mdb,
                 tmin=None,
                 tmax=None,
                 width=None,
                 selected_indices=None):
        self.name = name
        self.mdb = mdb
        self.tmax = tmax
        self.tmin = tmin
        self.width = width
        self.n_trials = None
        self.data_extractors = {}
        self.strategies = {}
        self.Data = DataView()
        self.Data.setup(self)
        self.DataSplitEvaluation = DataSplitEvaluation(self)
        self.selected_indices = selected_indices  # list/nested list of integer indices for selected simulation trials
        # for remote optimization
        self.results_remote = False  # flag, false if we have all results locally

    def add_data_extractor(self, name, data_extractor, setup=True):
        self.data_extractors[name] = data_extractor
        if setup == True:
            data_extractor.setup(self)

    def add_strategy(self, strategy, setup=True, view=None):
        name = strategy.name
        assert name not in self.strategies.keys()
        self.strategies[name] = strategy
        if view is None:
            view = self.Data
        if setup:
            strategy.setup(view, self.DataSplitEvaluation)

    def get_n_trials(self):
        if self.n_trials is None:
            self.n_trials = len(self.Data['y'])
        return self.n_trials

    def extract(self, name):
        return self.data_extractors[name].get()

    def run(self, client=None, n_workers=None, strategy_selection=None):
        for strategy_name in sorted(self.strategies.keys()):
            if strategy_selection is not None:
                if not strategy_name in strategy_selection:
                    continue
            strategy = self.strategies[strategy_name]
            for solver_name in sorted(strategy.solvers.keys()):
                solver = strategy.solvers[solver_name]
                if client is not None:
                    print('starting remote optimization'
                         ), strategy_name, solver_name
                    workers = client.scheduler_info()['workers'].keys()
                    workers = get_n_workers_per_ip(workers, n_workers)
                    solver.optimize_all_splits(client, workers=workers)
                    self.results_remote = True
                else:
                    print('starting local optimization'
                         ), strategy_name, solver_name
                    solver.optimize_all_splits()

    def _gather_results(self, client):
        assert client is not None
        self.DataSplitEvaluation.optimizer_results = \
            client.gather(self.DataSplitEvaluation.optimizer_results)
        self.results_remote = False

    def get_results(self, client=None):
        if self.results_remote:
            self._gather_results(client)
        return self.DataSplitEvaluation.compute_scores()


class Strategy(object):

    def __init__(self, name):
        self.name = name
        self.solvers = {}
        # self.split = None
        self.cupy_split = None
        self.numpy_split = None
        self.setup_done = False

    def setup(self, data, DataSplitEvaluation):
        if self.setup_done:
            return
        self.data = data
        self.DataSplitEvaluation = DataSplitEvaluation
        self.y = self.data['y'].values.astype('f4')
        self._setup()
        self.get_y = I.partial(self.get_y_static, self.y)
        self.get_score = I.partial(self.get_score_static, self._get_score)
        self._objective_function = I.partial(self._objective_function_static,
                                             self.get_score, self.get_y)
        self.setup_done = True

    def _setup(self):
        pass

    def _get_x0(self):
        pass

    def set_split(self, split, setup=True):
        cupy_split = make_weakref(
            np.array(split))  # cupy, if cupy is there, numpy otherwise
        numpy_split = numpy.array(split)  # allways numpy
        self.get_score = I.partial(self.get_score_static,
                                   self._get_score,
                                   cupy_split=cupy_split)
        self.get_y = I.partial(self.get_y_static,
                               self.y,
                               numpy_split=numpy_split)
        self._objective_function = I.partial(self._objective_function_static,
                                             self.get_score, self.get_y)
        if setup:
            for solver in self.solvers.values():
                solver._setup()
        return self

    @staticmethod
    def get_score_static(_get_score, x, cupy_split=None):
        x = np.array(x).astype('f4')
        score = _get_score(x)
        #         assert len(score[dereference(cupy_split)]) < len(score)

        if cupy_split is not None:
            return score[dereference(cupy_split)]
        else:
            return score

    @staticmethod
    def get_y_static(y, numpy_split=None):
        #         assert len(y[numpy_split]) <len(y)
        if numpy_split is not None:
            return y[numpy_split]
        else:
            return y

    @staticmethod
    def _objective_function_static(get_score, get_y, x):
        s = get_score(x)
        y = get_y()
        return -1 * sklearn.metrics.roc_auc_score(y, convert_to_numpy(s))

    def add_solver(self, solver, setup=True):
        assert solver.name not in self.solvers.keys()
        self.solvers[solver.name] = solver
        if setup:
            solver.setup(self)


class Solver(object):

    def __init__(self, name):
        self.name = name

    def setup(self, strategy):
        self.strategy = strategy
        self._setup()

    def _setup(self):
        pass

    def optimize_all_splits(self, client=None, workers=None):
        out = {}
        for name, split in self.strategy.DataSplitEvaluation.splits.iteritems():
            x0 = self.strategy._get_x0()
            self.strategy.set_split(split['train'])
            if client:

                out[name] = client.submit(self.optimize, x0=x0, workers=workers)
            else:
                out[name] = self.optimize(x0=x0)
        self.strategy.DataSplitEvaluation.add_result(self, out)
        return out

    def optimize_one_split(self, client=None, workers=None, index=0):  #rieke
        out = {}
        names = sorted(self.strategy.DataSplitEvaluation.splits.keys())
        #         for name, split in self.strategy.DataSplitEvaluation.splits.iteritems():
        name = names[index]
        split = self.strategy.DataSplitEvaluation.splits[name]
        x0 = self.strategy._get_x0()
        self.strategy.set_split(split['train'])
        if client:
            out[name] = client.submit(self.optimize, x0=x0, workers=workers)
        else:
            out[name] = self.optimize(x0=x0)
        self.strategy.DataSplitEvaluation.add_result(self, out)
        return out


class DataExtractor(object):

    def get(self):
        pass

    def setup(self, Rm):
        pass


class DataView(object):

    def __init__(self, mapping_dict={}):
        self.mapping_dict = mapping_dict

    def setup(self, Rm):
        self.Rm = Rm

    def __getitem__(self, key):
        if not key in self.mapping_dict:
            return self.Rm.extract(key)
        else:
            return self.Rm.extract(self.mapping_dict[key])


class DataSplitEvaluation(object):
    '''class used to split data in training/test sets and 
    evaluating performance scores corresponding to the splits'''

    def __init__(self, Rm):
        self.Rm = Rm
        self.splits = {}
        self.solvers = []
        self.optimizer_results = []
        self.optimizer_results_keys = []
        self.scores = []
        self.scores_keys = []

    def add_random_split(self, name, percentage_train=.7, l=None):
        assert name not in self.splits.keys()
        if l is None:
            n = self.Rm.get_n_trials()
            l = range(n)
        else:
            n = len(l)
        np.random.shuffle(np.array(l))
        train = l[:int(n * percentage_train)]
        test = l[int(n * percentage_train):]
        subtest1 = test[:int(len(test) / 2)]
        subtest2 = test[int(len(test) / 2):]
        self.splits[name] = {
            'train': train,
            'test': test,
            'subtest1': subtest1,
            'subtest2': subtest2
        }

    def add_isi_dependent_random_split(self,
                                       name,
                                       min_isi=10,
                                       percentage_train=.7):
        assert name not in self.splits.keys()
        ISI = self.Rm.extract('ISI') * -1
        ISI = ISI.fillna(min_isi + 1)
        ISI = ISI.reset_index(drop=True)
        l = list(ISI[ISI >= min_isi].index)
        self.add_random_split(name, percentage_train=percentage_train, l=l)

    def get_splits(self):
        return self.splits

    def add_result(self, solver, x):
        #         assert len(self.splits) == len(x) #rieke - want to run individual splits sometimes
        # assert solver.strategy.Rm is self.Rm
        solver_name = solver.name
        strategy_name = solver.strategy.name
        run = len([
            k for k in self.optimizer_results_keys
            if k[0] == strategy_name and k[1] == solver_name
        ])
        self.optimizer_results_keys.append((strategy_name, solver_name, run))
        self.optimizer_results.append(x)
        self.solvers.append(solver)

    def compute_scores(self):
        strategy_index = []
        solver_index = []
        split_index = []
        subsplit_index = []
        success_index = []
        score_index = []
        x_index = []
        runs_index = []
        for k, solver, x in zip(self.optimizer_results_keys, self.solvers,
                                self.optimizer_results):
            for split_name, xx in x.iteritems():
                split = self.splits[split_name]
                for subsplit_name, subsplit in split.iteritems():
                    runs_index.append(k[2])
                    x_index.append(xx.x)
                    success_index.append(xx.success)
                    solver_index.append(solver.name)
                    strategy = solver.strategy
                    strategy_index.append(strategy.name)
                    split_index.append(split_name)
                    subsplit_index.append(subsplit_name)
                    score = strategy.set_split(subsplit)._objective_function(
                        xx.x)
                    score_index.append(score)
        out = {
            'strategy': strategy_index,
            'solver': solver_index,
            'split': split_index,
            'subsplit': subsplit_index,
            'run': runs_index,
            'score': score_index,
            'x': x_index,
            'success': success_index
        }
        out = pd.DataFrame(out)
        out = out.set_index(['strategy', 'solver', 'split', 'subsplit',
                             'run']).sort_index()
        return out


class RaisedCosineBasis(object):

    def __init__(self,
                 a=2,
                 c=1,
                 phis=numpy.arange(1, 11, 0.5),
                 width=80,
                 reversed_=False,
                 backend=numpy):
        self.a = a
        self.c = c
        self.phis = phis
        self.reversed_ = reversed_
        self.backend = backend
        self.width = width
        self.compute(self.width)

    def compute(self, width=80):
        self.width = width
        self.t = numpy.arange(width)
        rev = -1 if self.reversed_ else 1
        self.basis = [
            make_weakref(
                self.get_raised_cosine(self.a,
                                       self.c,
                                       phi,
                                       self.t,
                                       backend=self.backend)[1][::rev])
            for phi in self.phis
        ]
        return self

    def get(self):
        return self.basis

    def get_superposition(self, x):
        return sum([b * xx for b, xx in zip(self.basis, x)])

    def visualize(self, ax=None, plot_kwargs={}):
        if ax is None:
            ax = plt.figure().add_subplot(111)
        for b in self.get():
            ax.plot(self.t, b, **plot_kwargs)

    def visualize_x(self, x, ax=None, plot_kwargs={}):
        if ax is None:
            ax = plt.figure().add_subplot(111)
        ax.plot(self.t, self.get_superposition(x), **plot_kwargs)

    @staticmethod
    def get_raised_cosine(a=1,
                          c=1,
                          phi=0,
                          t=numpy.arange(0, 80, 1),
                          backend=numpy):
        cos_arg = a * numpy.log(t + c) - phi
        v = .5 * numpy.cos(cos_arg) + .5
        v[cos_arg >= numpy.pi] = 0
        v[cos_arg <= -numpy.pi] = 0
        return backend.array(t.astype('f4')), backend.array(v.astype('f4'))


## data extractors
class DataExtractor_spatiotemporalSynapseActivation(DataExtractor):
    '''extracts array of the shape (trial, time, space) from spatiotemporal synapse activation binning'''

    def __init__(self, key):
        self.key = key
        self.data = None

    def setup(self, Rm):
        self.mdb = Rm.mdb
        self.tmin = Rm.tmin
        self.tmax = Rm.tmax
        self.width = Rm.width
        self.selected_indices = Rm.selected_indices
        self.data = {
            g: self._get_spatiotemporal_input(g) for g in self.get_groups()
        }

    @staticmethod
    def get_spatial_bin_level(key):
        '''returns the index that relects the spatial dimension'''
        return key[-1].split('__').index('binned_somadist')

    def get_spatial_binsize(self):
        '''returns spatial binsize'''
        mdb = self.mdb[0] if type(mdb) == list else self.mdb
        key = self.key
        level = self.get_spatial_bin_level(key)
        spatial_binsize = mdb[key].keys()[0][level]  # something like '100to150'
        spatial_binsize = spatial_binsize.split('to')
        spatial_binsize = float(spatial_binsize[1]) - float(spatial_binsize[0])
        return spatial_binsize

    def get_groups(self):
        '''returns all groups other than spatial binning'''
        mdb = self.mdb
        if type(mdb) != list:
            mdb = [mdb]
        key = self.key
        level = self.get_spatial_bin_level(key)
        out = []
        for single_mdb in mdb:  #rieke
            for k in single_mdb[key].keys():
                k = list(k)
                k.pop(level)
                out.append(tuple(k))
        return set(out)


#     def get_sorted_keys_by_group(self, group):

    def get_sorted_keys_by_group(self, group, mdb=None):  #rieke
        '''returns keys sorted such that the first key is the closest to the soma'''
        if mdb == None:  #rieke bc
            mdb = self.mdb
        mdb = mdb[0] if type(mdb) == list else mdb
        key = self.key
        group = list(group)
        level = self.get_spatial_bin_level(key)
        keys = mdb[key].keys()
        keys = sorted(keys, key=lambda x: float(x[level].split('to')[0]))
        out = []
        for k in keys:
            k_copy = list(k[:])
            k_copy.pop(level)
            if k_copy == group:
                out.append(k)
        return out

    def _get_spatiotemporal_input(self, group):
        '''returns spatiotemporal input in the following dimensions:
        (trial, time, space)'''
        mdb = self.mdb
        if type(mdb) != list:
            mdb = [mdb]
        key = self.key
        #         keys = self.get_sorted_keys_by_group(group)
        #         out = [mdb[key][k][:,self.tmax-self.width:self.tmax] for k in keys]
        #         out = numpy.dstack(out)

        outs = []
        for m, single_mdb in enumerate(mdb):
            keys = self.get_sorted_keys_by_group(group, mdb=single_mdb)
            if self.selected_indices is not None:
                out = [
                    single_mdb[key][k][self.selected_indices[m],
                                       self.tmax - self.width:self.tmax]
                    for k in keys
                ]
            else:
                out = [
                    single_mdb[key][k][:, self.tmax - self.width:self.tmax]
                    for k in keys
                ]
            out = numpy.dstack(out)
            outs.append(out)

        outs = numpy.concatenate(outs, axis=0)
        print(outs.shape)
        return outs

    def get(self):
        '''returns dictionary with groups as keys and spatiotemporal inputpatterns as keys.
        E.g. if the synapse activation is grouped by excitatory / inhibitory identity and spatial bins,
        the dictionary would be {'EXC': matrix_with_dimensions[trial, time, space], 
                                 'INH': matrix_with_dimensions[trial, time, space]}'''
        return self.data  # {g: self.get_spatiotemporal_input(g) for g in self.get_groups()}


class DataExtractor_categorizedTemporalSynapseActivation(DataExtractor):

    def __init__(self, key):
        self.key = key
        self.data = None

    def setup(self, Rm):
        self.mdb = Rm.mdb
        self.tmin = Rm.tmin
        self.tmax = Rm.tmax
        self.width = Rm.width
        self.selected_indices = Rm.selected_indices
        self._set_data()

    def _set_data(self):
        mdbs = self.mdb
        if type(mdbs) != list:
            mdbs = [mdbs]
        key = self.key
        keys = mdbs[0][key].keys()
        out = {}
        outs = []
        for k in keys:
            out[k] = []
            for m in mdbs:
                #print set(m[key].keys())
                #print keys
                assert set(m[key].keys()) == set(keys)
                if self.selected_indices is None:
                    out[k].append(m[key][k][:,
                                            self.tmax - self.width:self.tmax])
                else:
                    out[k].append(m[key][k][self.selected_indices,
                                            self.tmax - self.width:self.tmax])
            out[k] = numpy.vstack(out[k])
        self.data = out

    def get(self):
        return self.data


from simrun3.modular_reduced_model_inference import RaisedCosineBasis, numpy, make_weakref, np


class Strategy_categorizedTemporalRaisedCosine(Strategy):
    '''requires keys: spatiotemporalSa, st, y, ISI'''

    def __init__(self, name, RaisedCosineBasis_temporal):
        super(Strategy_categorizedTemporalRaisedCosine, self).__init__(name)
        self.RaisedCosineBasis_temporal = RaisedCosineBasis_temporal

    def _setup(self):
        self.compute_basis()
        self.groups = sorted(self.base_vectors_arrays_dict.keys())
        self.len_t, self.len_trials = self.base_vectors_arrays_dict.values(
        )[0].shape
        self._get_score = I.partial(self._get_score_static,
                                    self.base_vectors_arrays_dict)

    def compute_basis(self):
        '''computes_base_vector_array with shape (spatial, temporal, trials)'''
        st = self.data['st']
        stSa_dict = self.data['categorizedTemporalSa']
        base_vectors_arrays_dict = {}

        for group, tSa in stSa_dict.iteritems():
            len_trials, len_t = tSa.shape
            base_vector_rows = []
            for t in self.RaisedCosineBasis_temporal.compute(len_t).get():
                base_vector_rows.append(numpy.dot(tSa, t))
            base_vectors_arrays_dict[group] = make_weakref(
                np.array(numpy.array(base_vector_rows).astype('f4')))
        self.base_vectors_arrays_dict = base_vectors_arrays_dict
        self.keys = sorted(base_vectors_arrays_dict.keys())

    def _get_x0(self):
        return numpy.random.rand(self.len_t * len(self.groups)) * 2 - 1

    @staticmethod
    def _get_score_static(base_vectors_arrays_dict, x):
        outs = []
        x_reshaped = x.reshape(len(base_vectors_arrays_dict), -1)
        keys = sorted(base_vectors_arrays_dict.keys())
        for lv, group in enumerate(keys):
            array = base_vectors_arrays_dict[group]
            x_current = x_reshaped[lv, :]
            out = np.dot(dereference(x_current), dereference(array)).squeeze()
            outs.append(out)
        return np.vstack(outs).sum(axis=0)


class DataExtractor_spiketimes(DataExtractor):

    def setup(self, Rm):
        self.mdb = Rm.mdb
        self.st = None
        self.selected_indices = Rm.selected_indices

    def get(self):
        if type(self.mdb) != list:
            return self.mdb['spike_times']
        else:
            st_list = []
            if self.selected_indices is not None:
                for m, single_mdb in enumerate(self.mdb):
                    st_list.append(single_mdb['spike_times'].iloc[
                        self.selected_indices[m]])
            else:
                for single_mdb in self.mdb:
                    st_list.append(single_mdb['spike_times'])
            return pd.concat(st_list)


class DataExtractor_object(DataExtractor):

    def __init__(self, key):
        self.key = key

    def setup(self, Rm):
        self.mdb = Rm.mdb
        self.data = Rm[self.key]  #rieketodo

    def get(self):
        return self.data


class DataExtractor_spikeInInterval(DataExtractor):

    def __init__(self, tmin=None, tmax=None):
        self.tmin = tmin
        self.tmax = tmax

    def setup(self, Rm):
        if self.tmin is None:
            self.tmin = Rm.tmin
        if self.tmax is None:
            self.tmax = Rm.tmax
        self.mdb = Rm.mdb
        self.selected_indices = Rm.selected_indices

        if type(self.mdb) != list:
            st = self.mdb['spike_times']
        else:
            st_list = []
            if self.selected_indices is not None:
                for m, single_mdb in enumerate(self.mdb):
                    st_list.append(single_mdb['spike_times'].iloc[
                        self.selected_indices[m]])
            else:
                for single_mdb in self.mdb:
                    st_list.append(single_mdb['spike_times'])
            st = pd.concat(st_list)

        self.sii = I.spike_in_interval(st, tmin=self.tmin, tmax=self.tmax)

    def get(self):
        return self.sii


class DataExtractor_ISI(DataExtractor):

    def __init__(self, t=None):
        self.t = t

    def setup(self, Rm):
        self.mdb = Rm.mdb
        if self.t is None:
            self.t = Rm.tmin
        self.selected_indices = Rm.selected_indices

        if type(self.mdb) != list:
            st = self.mdb['spike_times']
        else:
            st_list = []
            if self.selected_indices is not None:
                for m, single_mdb in enumerate(self.mdb):
                    st_list.append(single_mdb['spike_times'].iloc[
                        self.selected_indices[m]])
            else:
                for single_mdb in self.mdb:
                    st_list.append(single_mdb['spike_times'])
            st = pd.concat(st_list)

        t = self.t
        st[st > t] = numpy.NaN
        self.ISI = st.max(axis=1) - t

    def get(self):
        return self.ISI


class DataExtractor_daskDataframeColumn(DataExtractor):  #rieketodo

    def __init__(self, key, column, client=None):
        if not isinstance(key, tuple):
            self.key = (key,)
        else:
            self.key = key
        self.column = column
        self.client = client
        self.data = None

    def setup(self, Rm):
        self.mdb = Rm.mdb
        cache = self.mdb.create_sub_mdb(
            'DataExtractor_daskDataframeColumn_cache', raise_=False)
        complete_key = list(self.key) + [self.column]
        complete_key = map(str, complete_key)
        complete_key = tuple(complete_key)
        print(complete_key)
        if not complete_key in cache.keys():
            slice_ = self.mdb[self.key][self.column]
            slice_ = self.client.compute(slice_).result()
            cache.setitem(complete_key,
                          slice_,
                          dumper=I.dumper_pandas_to_parquet)
        self.data = cache[complete_key]
        # after the setup, the object must be serializable and therefore must not contain a client objectz
        self.client = None

    def get(self):
        return self.data


class Solver_COBYLA(Solver):

    def __init__(self, name):
        self.name = name

    def _setup(self):
        self.optimize = I.partial(self._optimize,
                                  self.strategy._objective_function,
                                  maxiter=5000)

    @staticmethod
    def _optimize(_objective_function, maxiter=5000, x0=None):
        out = scipy.optimize.minimize(_objective_function,
                                      x0,
                                      method='COBYLA',
                                      options=dict(maxiter=maxiter, disp=True))
        return out


class Strategy_ISIcutoff(Strategy):

    def __init__(self, name, cutoff_range=(0, 4), penalty=-10**10):
        super(Strategy_ISIcutoff, self).__init__(name)
        self.cutoff_range = cutoff_range
        self.penalty = penalty

    def _setup(self):
        self.ISI = make_weakref(np.array(self.data['ISI'].fillna(-100)))
        self._get_score = I.partial(self._get_score_static, self.ISI,
                                    self.penalty)

    @staticmethod
    def _get_score_static(ISI, penalty, x):
        ISIc = ISI.copy()
        x = x[0] * -1
        ISIc[ISI <= x] = 0
        ISIc[ISI > x] = penalty
        return ISIc

    def _get_x0(self):
        min_ = self.cutoff_range[0]
        max_ = self.cutoff_range[1]
        return numpy.random.rand(1) * (max_ - min_) + min_


class Strategy_ISIexponential(Strategy):

    def __init__(self, name, max_isi=100):
        super(Strategy_ISIexponential, self).__init__(name)
        self.name = name
        self.max_isi = 100

    def _setup(self):
        ISI = self.data['ISI']
        ISI = ISI * -1
        ISI = ISI.fillna(self.max_isi)
        self.ISI = ISI
        self._get_score = I.partial(self._get_score_static, self.ISI)

    @staticmethod
    def _get_x0():
        return (numpy.random.rand(2) * numpy.array([-10, 15]))

    @staticmethod
    def _get_score_static(ISI, x):
        ISI = ISI.replace([np.inf, -np.inf], np.nan).fillna(-10**10).values
        return np.array(ISI)

    def visualize(self, optimizer_output, normalize=True):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        x = np.arange(0, 50)
        for o in optimizer_output:
            v = -1 * np.exp(o.x[0] * (x - x[1]))
            if normalize:
                v = v / np.max(np.abs(v))
            ax.plot(v)


class Strategy_ISIraisedCosine(Strategy):

    def __init__(self, name, RaisedCosineBasis_postspike):
        super(Strategy_ISIraisedCosine, self).__init__(name)
        # datatype needs to match backend, recompute
        self.RaisedCosineBasis_postspike = RaisedCosineBasis_postspike
        RaisedCosineBasis_postspike.backend = np
        RaisedCosineBasis_postspike.compute()

    def _setup(self):
        ISI = self.data['ISI']
        ISI = ISI * -1
        width = self.RaisedCosineBasis_postspike.width
        ISI[ISI >= width] = width
        ISI = ISI.fillna(width)
        ISI = ISI.astype(int) - 1
        self.ISI = make_weakref(np.array(ISI))
        self._get_score = I.partial(self._get_score_static,
                                    self.RaisedCosineBasis_postspike, self.ISI)

    def _get_x0(self):
        return (numpy.random.rand(len(self.RaisedCosineBasis_postspike.phis)) *
                2 - 1) * 5

    @staticmethod
    def _get_score_static(RaisedCosineBasis_postspike, ISI, x):
        kernel = RaisedCosineBasis_postspike.get_superposition(x)
        return kernel[dereference(ISI)]

    def visualize(self, optimizer_output, normalize=True, only_succesful=True):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        for x in optimizer_output:
            if only_succesful:
                if not x.success:
                    continue
            if normalize:
                v = self.normalize_x(x.x)
            else:
                v = self.RaisedCosineBasis_postspike.get_superposition(x.x)
            ax.plot(v)

    def normalize_x(self, x):
        v = self.RaisedCosineBasis_postspike.get_superposition(x)
        v = v - [v[-1]]
        v = v / np.abs(v[0])
        return v


class Strategy_spatiotemporalRaisedCosine(Strategy):
    '''requires keys: spatiotemporalSa, st, y, ISI'''

    def __init__(self, name, RaisedCosineBasis_spatial,
                 RaisedCosineBasis_temporal):
        super(Strategy_spatiotemporalRaisedCosine, self).__init__(name)
        self.RaisedCosineBasis_spatial = RaisedCosineBasis_spatial
        self.RaisedCosineBasis_temporal = RaisedCosineBasis_temporal

    def _setup(self):
        self.compute_basis()
        self.groups = sorted(self.base_vectors_arrays_dict.keys())
        self.len_z, self.len_t, self.len_trials = self.base_vectors_arrays_dict.values(
        )[0].shape
        self.convert_x = I.partial(self._convert_x_static, self.groups,
                                   self.len_z)
        self._get_score = I.partial(self._get_score_static, self.convert_x,
                                    self.base_vectors_arrays_dict)

    def compute_basis(self):
        '''computes_base_vector_array with shape (spatial, temporal, trials)'''
        st = self.data['st']
        stSa_dict = self.data['spatiotemporalSa']
        base_vectors_arrays_dict = {}
        for group, stSa in stSa_dict.iteritems():
            len_trials, len_t, len_z = stSa.shape
            base_vector_array = []
            for z in self.RaisedCosineBasis_spatial.compute(len_z).get():
                base_vector_row = []
                tSa = numpy.dot(stSa, z).squeeze()
                for t in self.RaisedCosineBasis_temporal.compute(len_t).get():
                    base_vector_row.append(numpy.dot(tSa, t))
                base_vector_array.append(base_vector_row)
            base_vectors_arrays_dict[group] = make_weakref(
                np.array(numpy.array(base_vector_array).astype('f4')))
        self.base_vectors_arrays_dict = base_vectors_arrays_dict

    def _get_x0(self):
        return numpy.random.rand(
            (self.len_z + self.len_t) * len(self.groups)) * 2 - 1

    @staticmethod
    def _convert_x_static(groups, len_z, x):
        len_groups = len(groups)
        out = {}
        x = x.reshape(len_groups, len(x) / len_groups)
        for lv, group in enumerate(groups):
            x_z = x[lv, :len_z]
            x_t = x[lv, len_z:]
            out[group] = x_z, x_t
        return out

    @staticmethod
    def _get_score_static(convert_x, base_vectors_arrays_dict, x):
        outs = []
        for group, (x_z, x_t) in convert_x(x).iteritems():
            array = base_vectors_arrays_dict[group]
            out = np.dot(dereference(x_t), dereference(array)).squeeze()
            out = np.dot(dereference(x_z), dereference(out)).squeeze()
            outs.append(out)
        return np.vstack(outs).sum(axis=0)

    def normalize(self, x, flipkey=None):
        '''normalize such that exc and inh peak is at 1 and -1, respectively.
        normalize, such that sum of all absolute values of all kernels is 1'''
        x = self.convert_x(x)
        #temporal
        b = self.RaisedCosineBasis_temporal
        x_exc_t = x[('EXC',)][1]
        x_inh_t = x[('INH',)][1]
        x_exc_z = x[('EXC',)][0]
        x_inh_z = x[('INH',)][0]
        norm_exc = b.get_superposition(x_exc_t)[np.argmax(
            np.abs(b.get_superposition(x_exc_t)))]
        norm_inh = -1 * b.get_superposition(x_inh_t)[np.argmax(
            np.abs(b.get_superposition(x_inh_t)))]
        # spatial
        b = self.RaisedCosineBasis_spatial
        # norm_spatial = sum(np.abs(b.get_superposition(x_exc_z)) + np.abs(b.get_superposition(x_inh_z)))
        norm_spatial = max(np.abs(b.get_superposition(x_exc_z * norm_exc)))
        # print norm_exc, norm_inh, norm_spatial
        x[('EXC',)] = (x_exc_z * norm_exc / norm_spatial, x_exc_t / norm_exc)
        x[('INH',)] = (x_inh_z * norm_inh / norm_spatial, x_inh_t / norm_inh)
        # output
        x_out = []
        for group in self.groups:
            x_out += list(x[group][0]) + list(x[group][1])
        return np.array(x_out)

    def get_color_by_group(self, group):
        if 'EXC' in group:
            return 'r'
        elif 'INH' in group:
            return 'grey'
        else:
            return None

    def visualize(self,
                  optimizer_output,
                  only_successful=False,
                  normalize=True):
        fig = plt.figure(figsize=(10, 5))
        ax_z = fig.add_subplot(1, 2, 1)
        ax_t = fig.add_subplot(1, 2, 2)
        for out in optimizer_output:
            if only_successful:
                if not out.success:
                    continue
            if normalize:
                dict_ = self.convert_x(self.normalize(out.x))
            else:
                dict_ = self.convert_x(out.x)
            for group, (x_z, x_t) in dict_.iteritems():
                c = self.get_color_by_group(group)
                self.RaisedCosineBasis_temporal.visualize_x(
                    x_t, ax=ax_t, plot_kwargs={'c': c})
                self.RaisedCosineBasis_spatial.visualize_x(x_z,
                                                           ax=ax_z,
                                                           plot_kwargs={'c': c})


class Strategy_temporalRaisedCosine_spatial_cutoff(Strategy):
    '''requires keys: temporalSa, st, y, ISI'''

    def __init__(self, name, RaisedCosineBasis_spatial,
                 RaisedCosineBasis_temporal):
        super(Strategy_spatiotemporalRaisedCosine, self).__init__(name)
        self.RaisedCosineBasis_spatial = RaisedCosineBasis_spatial
        self.RaisedCosineBasis_temporal = RaisedCosineBasis_temporal

    def _setup(self):
        self.compute_basis()
        self.groups = sorted(self.base_vectors_arrays_dict.keys())
        self.len_z, self.len_t, self.len_trials = self.base_vectors_arrays_dict.values(
        )[0].shape
        self.convert_x = I.partial(self._convert_x_static, self.groups,
                                   self.len_z)
        self._get_score = I.partial(self._get_score_static, self.convert_x,
                                    self.base_vectors_arrays_dict)

    def compute_basis(self):
        '''computes_base_vector_array with shape (spatial, temporal, trials)'''
        st = self.data['st']
        stSa_dict = self.data['spatiotemporalSa']
        base_vectors_arrays_dict = {}
        for group, stSa in stSa_dict.iteritems():
            len_trials, len_t, len_z = stSa.shape
            base_vector_array = []
            for z in self.RaisedCosineBasis_spatial.compute(len_z).get():
                base_vector_row = []
                tSa = numpy.dot(stSa, z).squeeze()
                for t in self.RaisedCosineBasis_temporal.compute(len_t).get():
                    base_vector_row.append(numpy.dot(tSa, t))
                base_vector_array.append(base_vector_row)
            base_vectors_arrays_dict[group] = make_weakref(
                np.array(numpy.array(base_vector_array).astype('f4')))
        self.base_vectors_arrays_dict = base_vectors_arrays_dict

    def _get_x0(self):
        return numpy.random.rand(
            (self.len_z + self.len_t) * len(self.groups)) * 2 - 1

    @staticmethod
    def _convert_x_static(groups, len_z, x):
        len_groups = len(groups)
        out = {}
        x = x.reshape(len_groups, len(x) / len_groups)
        for lv, group in enumerate(groups):
            x_z = x[lv, :len_z]
            x_t = x[lv, len_z:]
            out[group] = x_z, x_t
        return out

    @staticmethod
    def _get_score_static(convert_x, base_vectors_arrays_dict, x):
        outs = []
        for group, (x_z, x_t) in convert_x(x).iteritems():
            array = base_vectors_arrays_dict[group]
            out = np.dot(dereference(x_t), dereference(array)).squeeze()
            out = np.dot(dereference(x_z), dereference(out)).squeeze()
            outs.append(out)
        return np.vstack(outs).sum(axis=0)

    def normalize(self, x, flipkey=None):
        '''normalize such that exc and inh peak is at 1 and -1, respectively.
        normalize, such that sum of all absolute values of all kernels is 1'''
        x = self.convert_x(x)
        #temporal
        b = self.RaisedCosineBasis_temporal
        x_exc_t = x[('EXC',)][1]
        x_inh_t = x[('INH',)][1]
        x_exc_z = x[('EXC',)][0]
        x_inh_z = x[('INH',)][0]
        norm_exc = b.get_superposition(x_exc_t)[np.argmax(
            np.abs(b.get_superposition(x_exc_t)))]
        norm_inh = -1 * b.get_superposition(x_inh_t)[np.argmax(
            np.abs(b.get_superposition(x_inh_t)))]
        # spatial
        b = self.RaisedCosineBasis_spatial
        # norm_spatial = sum(np.abs(b.get_superposition(x_exc_z)) + np.abs(b.get_superposition(x_inh_z)))
        norm_spatial = max(np.abs(b.get_superposition(x_exc_z * norm_exc)))
        # print norm_exc, norm_inh, norm_spatial
        x[('EXC',)] = (x_exc_z * norm_exc / norm_spatial, x_exc_t / norm_exc)
        x[('INH',)] = (x_inh_z * norm_inh / norm_spatial, x_inh_t / norm_inh)
        # output
        x_out = []
        for group in self.groups:
            x_out += list(x[group][0]) + list(x[group][1])
        return np.array(x_out)

    def get_color_by_group(self, group):
        if 'EXC' in group:
            return 'r'
        elif 'INH' in group:
            return 'grey'
        else:
            return None

    def visualize(self,
                  optimizer_output,
                  only_successful=False,
                  normalize=True):
        fig = plt.figure(figsize=(10, 5))
        ax_z = fig.add_subplot(1, 2, 1)
        ax_t = fig.add_subplot(1, 2, 2)
        for out in optimizer_output:
            if only_successful:
                if not out.success:
                    continue
            if normalize:
                dict_ = self.convert_x(self.normalize(out.x))
            else:
                dict_ = self.convert_x(out.x)
            for group, (x_z, x_t) in dict_.iteritems():
                c = self.get_color_by_group(group)
                self.RaisedCosineBasis_temporal.visualize_x(
                    x_t, ax=ax_t, plot_kwargs={'c': c})
                self.RaisedCosineBasis_spatial.visualize_x(x_z,
                                                           ax=ax_z,
                                                           plot_kwargs={'c': c})


class Strategy_linearCombinationOfData(Strategy):

    def __init__(self, name, data_keys):
        super(Strategy_linearCombinationOfData, self).__init__(name)
        self.data_keys = data_keys
        self.data_values = None

    def _setup(self):
        self.data_values = np.array([self.data[k] for k in self.data_keys])
        self._get_score = I.partial(self._get_score_static, self.data_values)

    def _get_x0(self):
        return numpy.random.rand(len(self.data_keys)) * 2 - 1

    @staticmethod
    def _get_score_static(data_values, x):
        return np.dot(data_values.T, x)


class CombineStrategies_sum(Strategy):

    def __init__(self, name):
        super(CombineStrategies_sum, self).__init__(name)
        self.strategies = []
        self.lens = []
        self.split = None

    def setup(self, data, DataSplitEvaluation):
        super(CombineStrategies_sum, self).setup(data, DataSplitEvaluation)
        for s in self.strategies:
            s.setup(data, DataSplitEvaluation)
            self.lens.append(len(s._get_x0()))

    def set_split(self, split):
        super(CombineStrategies_sum, self).set_split(split)
        for s in self.strategies:
            s.set_split(split)
        return self

    def _setup(self):
        score_functions = [strategy.get_score for strategy in self.strategies]
        self._get_score = I.partial(self._get_score_static, score_functions,
                                    self.lens)

    def add_strategy(self, s, setup=True):
        self.strategies.append(s)

    @staticmethod
    def _get_score_static(score_functions, lens, x):
        out = 0
        len_ = 0
        for sf, l in zip(score_functions, lens):
            out += sf(x[len_:len_ + l])
            len_ += l
        return out

    def _get_x0(self):
        out = [s._get_x0() for s in self.strategies]
        return numpy.concatenate(out)
