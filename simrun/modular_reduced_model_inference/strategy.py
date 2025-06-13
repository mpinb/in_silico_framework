# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.

"""Strategies for creating reduced models.

Strategies are pipelines whose sole purpose is to define a cost function.
Cost functions are functions :math:`f: D, x \\rightarrow c` that take data :math:`D` and parameters :math:`x` as input and return some cost :math:`c`.
Solvers then optimize these cost functions to find the best parameters :math:`x` for the given data :math:`D`.

This approach is purposefully kept very general, so that it can be used for a wide range of purposes.

One such example is given in :cite:t:`Bast_Fruengel_Kock_Oberlaender_2024`.
Here, the strategy contains a set of raised cosine basis functions.
These are weighed and superimposed to create spatiotemporal filters. 
Once multiplied with synaptic activation data, they provided a weighed input of synapse activations.
This is then used to predict the spike probability based on the synaptic activation patterns.
The parameters that are being optimized are the weights of the raised cosine basis functions.

"""


import numpy as np
from functools import partial
import sklearn.metrics
import matplotlib.pyplot as plt
import weakref
import sys
from config.isf_logging import logger
CUPY_ENABLED = 'cupy' in sys.modules
if CUPY_ENABLED:
    import cupy
    np = cupy
else:
    logger.warning("CUPY is not available.")
    import numpy as np

# cupy frees GPU memory when all references are deleted
# as this is difficult to track, use the make_weakref method, which stores all
# GPU arrays in the _WEAKREF_ARRAY_LIST and returns a weakref object. This can be used to
# interact with the data, but is not a reference.
# Therefore, it is sufficient to empty _WEAKREF_ARRAY_LIST, which frees the GPU memory.
# All weakref objects pointing to GPU arrays will then be invalidated.
_WEAKREF_ARRAY_LIST = []

def make_weakref(obj):
    """Create a weak reference of a Python object.

    Objects saved on VRAM do not get cleared automatically,
    and memory management needs to be done manually.
    However, weak references get cleared by the Python garbage collector.
    This is a convenience method to convert Python objects to weak references,
    so that memory handling is more robust and practical.

    Attention:
        A weak reference is not the same as a direct reference.
        Objects with references to it (i.e; referents) do not get destroyed as long as a direct reference exists.
        This is not the case for weak references.
    """    
    _WEAKREF_ARRAY_LIST.append(obj)
    return weakref.proxy(obj)


def dereference(weakrefobj):
    '''Dereference a reference and fetch the referent.

    Attention:
        Uses private interface ... check after version update!

    See also:
        https://stackoverflow.com/questions/19621036/acquiring-a-regular-reference-from-a-weakref-proxy-in-python

    Args:
        weakrefobj (wearkef.proxy.object): The weak reference to an object.

    Returns:
        obj: The underlying referent object referred to by the wear reference.

    '''
    return weakrefobj.__repr__.__self__


def clear_memory():
    """Remove all weak references
    
    Cupy frees GPU memory when all references are deleted
    As this is difficult to track, use the :py:meth:`simrun.modular_reduced_model_inference.make_weakref` method, which storesall GPU arrays in the _WEAKREF_ARRAY_LIST and returns a weakref object. 
    This can be used to interact with the data, but is not a reference.
    Therefore, it is sufficient to empty _WEAKREF_ARRAY_LIST, which frees the GPU memory.
    All weakref objects pointing to GPU arrays will then be invalidated.
    """
    del _WEAKREF_ARRAY_LIST[:]


def convert_to_numpy(x):
    """Convert a numpy to a cupy array

    Only performs this conversion if CUPY is available.

    Args:
        x (cupy.array): the array to convert.
    """
    if CUPY_ENABLED:
        return cupy.asnumpy(x)
    else:
        return x


class _Strategy(object):
    """Strategy base class.
    
    This class is used to define a strategy for the optimizer. Each strategy sets up all necessary components
    to define a single cost function :py:meth:`get_score`. 
    This cost function is used by a :py:mod:`simrun.modular_reduced_model_inference.solver` 
    to optimize the parameters of the strategy.
    
    Each child class must implement a ``_get_score`` class method.
    These are used here to construct :py:meth:`~simrun.modular_reduced_model_inference._Strategy.get_score`.
    It is this `get_score` method that is optimized during optimization.
    
    As a function of the parameters, compute a value for each trial.
    The optimizer will optimize for this value (highest AUROC score)
    
    Needs some repr for input data.
    
    E.G. A strategy that needs to optimize for AP refractory, then the Strategy needs to incorporate this data
    """

    def __init__(self, name):
        """
        Args:
            name (str): The name of the strategy.
        """
        self.name = name
        self.solvers = {}
        # self.split = None
        self.cupy_split = None
        self.numpy_split = None
        
        # Attributes below are set in setup
        self.setup_done = False
        self.data = None
        self.DataSplitEvaluation = None
        self.y = None
        self.get_y = None
        self.get_score = None
        self._objective_function = None
        
    def _get_score(self, x):
        """Compute the score for the given parameters x.
        
        This method needs to be defined for each strategy.
        This score will be optimized by the solver.
        
        Example:
            :py:class:`~simrun.modular_reduced_model_inference.Strategy_categorizedTemporalRaisedCosine._get_score_static`,
            which is assigned to :py:meth:`~simrun.modular_reduced_model_inference.Strategy_categorizedTemporalRaisedCosine._get_score`.
        """
        pass

    def setup(self, data, DataSplitEvaluation):
        """Setup the strategy with the given data.
        
        This method sets up the strategy with the given data and the DataSplitEvaluation object.
        
        Strategy-specific setup is performed by :py:meth:`~simrun.modular_reduced_model_inference._Strategy._setup`,
        which is overloaded by child classes.
        
        Args:
            data (dict): The data to use.
            DataSplitEvaluation (:py:class:`~simrun.modular_reduced_model_inference.reduced_model.DataSplitEvaluation`): 
                The DataSplitEvaluation object to use.
        """
        if self.setup_done:
            return
        self.data = data
        self.DataSplitEvaluation = DataSplitEvaluation
        self.y = self.data['y'].values.astype('f4')
        self._setup()
        self.get_y = partial(self.get_y_static, self.y)
        self.get_score = partial(self.get_score_static, self._get_score)
        self._objective_function = partial(self._objective_function_static, self.get_score, self.get_y)
        self.setup_done = True

    def _setup(self):
        """Strategy-specific setup.
        
        This method is overloaded by child classes to provide setup specific for the Strategy.
        """
        pass

    def _get_x0(self):
        """Get an initial guess for the learnable weights of the basis functions :math:`\mathbf{x}`.
        
        This method is overloaded specific to the strategy.
        """
        pass

    def set_split(self, split, setup=True):
        """Set the split for this strategy.
        
        Scoring is usually performed on multiple splits of the data.
        This method assigns one such split to the strategy, so that
        all consequent calls to :py:meth:`get_score` and :py:meth:`get_y` will use this split.
        
        Args:
            split (array): An array of indices to use for the split.
            setup (bool): Whether to setup the strategy after setting the split. Default is ``True``.
            
        Returns:
            _Strategy: The strategy object with the split set.
            
        Example:

            >>> s = Strategy('test')
            >>> s.get_score()
            # returns a score for all data
            >>> s = s.set_split(np.array([0, 1, 2]))
            >>> s.get_score()
            # returns a score for the data at indices 0, 1, and 2
        """
        cupy_split = make_weakref(np.array(split))  # cupy, if cupy is there, numpy otherwise
        numpy_split = np.array(split)  # allways numpy
        self.get_score = partial(
            self.get_score_static,
            self._get_score,
            cupy_split=cupy_split)
        self.get_y = partial(
            self.get_y_static,
            self.y,
            numpy_split=numpy_split)
        self._objective_function = partial(
            self._objective_function_static,
            self.get_score, 
            self.get_y)
        if setup:
            for solver in self.solvers.values():
                solver._setup()
        return self

    @staticmethod
    def get_score_static(_get_score, x, cupy_split=None):
        """Convert the strategy-specific ``_get_score`` method to a static method.
        
        Args:
            _get_score (callable): The strategy-specific ``_get_score`` method.
            x (array): The input array.
            cupy_split (array): The array splits.
            
        Returns:
            array: The score.
        """
        x = np.array(x).astype('f4')
        score = _get_score(x)
        #         assert len(score[dereference(cupy_split)]) < len(score)

        if cupy_split is not None:
            return score[dereference(cupy_split)]
        else:
            return score

    @staticmethod
    def get_y_static(y, numpy_split=None):
        """Fetch the labels for the given split.
        
        Args:
            y (array): The labels.
            numpy_split (array): The split.
            
        Returns:
            array: The labels for the given split.
        """
        #         assert len(y[numpy_split]) <len(y)
        if numpy_split is not None:
            return y[numpy_split]
        else:
            return y

    @staticmethod
    def _objective_function_static(get_score, get_y, x):
        """Compute the objective value for the given parameters x.
        
        Calculates the score for the given parameters x and the labels y.
        Computes the AUROC score between the two.
        
        Attention:
            The AUROC score is here given as a negative value, as the optimizer tries to minimize the objective function.
            So a high AUROC score will result here in a very negative value.
            
        Returns:
            float: The negative AUROC score, between :math:`[-1, 0]`
        """
        s = get_score(x)
        y = get_y()
        return -1 * sklearn.metrics.roc_auc_score(y, convert_to_numpy(s))


    def add_solver(self, solver, setup=True):
        """Add a solver to the strategy.
        
        Args:
            solver (:py:class:`~simrun.modular_reduced_model_inference.solver.Solver`): The solver to add.
            setup (bool): Whether to setup the solver. Default is ``True``.
            
        Returns:
            None. Adds the solver to the strategy.
        """
        assert solver.name not in self.solvers.keys()
        self.solvers[solver.name] = solver
        if setup:
            solver.setup(self)


class Strategy_categorizedTemporalRaisedCosine(_Strategy):
    '''
    requires keys: spatiotemporalSa, st, y, ISI
    
    :skip-doc:
    '''

    def __init__(self, name, RaisedCosineBasis_temporal):
        super(Strategy_categorizedTemporalRaisedCosine, self).__init__(name)
        self.RaisedCosineBasis_temporal = RaisedCosineBasis_temporal

    def _setup(self):
        self.compute_basis()
        self.groups = sorted(self.base_vectors_arrays_dict.keys())
        self.len_t, self.len_trials = self.base_vectors_arrays_dict.values()[0].shape
        self._get_score = partial(
            self._get_score_static,
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
                base_vector_rows.append(np.dot(tSa, t))
            base_vectors_arrays_dict[group] = make_weakref(
                np.array(np.array(base_vector_rows).astype('f4')))
        self.base_vectors_arrays_dict = base_vectors_arrays_dict
        self.keys = sorted(base_vectors_arrays_dict.keys())

    def _get_x0(self):
        return np.random.rand(self.len_t * len(self.groups)) * 2 - 1

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


class Strategy_ISIcutoff(_Strategy):
    """:skip-doc:"""
    def __init__(self, name, cutoff_range=(0, 4), penalty=-10**10):
        super(Strategy_ISIcutoff, self).__init__(name)
        self.cutoff_range = cutoff_range
        self.penalty = penalty

    def _setup(self):
        self.ISI = make_weakref(np.array(self.data['ISI'].fillna(-100)))
        self._get_score = partial(self._get_score_static, self.ISI,self.penalty)

    @staticmethod
    def _get_score_static(ISI, penalty, x):
        """Compute the objective value for the given parameters x."""
        # hard cutoff for ISI.
        ISIc = ISI.copy()
        x = x[0] * -1
        ISIc[ISI <= x] = 0          # very good
        ISIc[ISI > x] = penalty     # very bad
        return ISIc

    def _get_x0(self):
        min_ = self.cutoff_range[0]
        max_ = self.cutoff_range[1]
        return np.random.rand(1) * (max_ - min_) + min_


class Strategy_ISIexponential(_Strategy):
    """TODO: is this fully implemented? There doesnt seem to be an actual exponential here...
    :skip-doc:
    """
    def __init__(self, name, max_isi=100):
        super(Strategy_ISIexponential, self).__init__(name)
        self.name = name
        self.max_isi = 100

    def _setup(self):
        ISI = self.data['ISI']
        ISI = ISI * -1
        ISI = ISI.fillna(self.max_isi)
        self.ISI = ISI
        self._get_score = partial(self._get_score_static, self.ISI)

    @staticmethod
    def _get_x0():
        return (np.random.rand(2) * np.array([-10, 15]))

    @staticmethod
    def _get_score_static(ISI, x):
        """NAN if no preceding AP"""
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


class RaisedCosineBasis(object):
    """Set of raised cosine basis functions to use as a kernel for weighing synaptic activation patterns.
    
    A raised cosine is defined as:
    
    .. math::
    
        f_i(x) = \\frac{1}{2} cos(a \cdot log(\\tau + c) - \phi_i) + \\frac{1}{2}
        
    where :math:`\\tau` is the input dimension (space or time e.g.), :math:`a` is the steepness, :math:`c` is the offset, and :math:`\phi` is the phase.
    These basis functions can be superimposed using learnable weights :math:`x_i` to form a single filter :math:`\mathbf{w}(\\tau)` over the domain :math:`\\tau`:
    
    .. math::
    
        \mathbf{w}(\\tau) = \sum_{i} x_i \cdot f_i(\\tau)
        
    And this filter can then be used to weigh the input data :math:`\mathbf{D}`:
    
    .. math::
    
        WI(t) = \int_{t-width}^{t}  \mathbf{w}(\\tau) \cdot \mathbf{D}(\\tau)
        
    Note:
        The notation here heavily implies that the cosine functions are defined over the time domain.
        However, they can equally well be used for spatial or spatiotemporal data.

    Attributes:
        a (int): The steepness of the raised cosine. Default is :math:`2`.
        c (int): The offset of the raised cosine. Default is :math:`1`.
        phis (array): The phases of the raised cosine. Default is ``np.arange(1, 11, 0.5)``.
        width (int): The width of the basis functions. Default is :math:`80`.
        basis (list): The list of basis functions.
        reversed_ (bool): Whether to reverse the basis functions. Default is ``False``.
        backend (module): The backend to use (cupy or numpy). Default is ``numpy``.
    """

    def __init__(
        self,
        a=2,
        c=1,
        phis=None,
        width=80,
        reversed_=False,
        backend=np):
        """
        Args:
            a (int): The steepness of the raised cosine. Default is :math:`2`.
            c (int): The offset of the raised cosine. Default is :math:`1`.
            phis (array): The phases of the raised cosine. Default is ``np.arange(1, 11, 0.5)``.
            width (int): The width of the basis functions. Default is :math:`80`.
            reversed_ (bool): Whether to reverse the basis functions. Default is ``False``.
            backend (module): The backend to use (cupy or numpy). Default is ``numpy``.
        """
        self.a = a
        self.c = c
        self.phis = phis if phis is not None else np.arange(1, 11, 0.5)
        self.reversed_ = reversed_
        self.backend = backend
        self.width = width
        self.basis = None
        self.compute(self.width)


    def compute(self, width=80):
        """Compute the vector of raised cosine basis functions :math:`\mathbf{f}`.
        
        Each element :math:`f_i` in the vector :math:`\mathbf{f}` is a raised cosine basis function 
        with a different :math:`\phi_i`. The domain of each :math:`f_i` is :math:`[0, width]`.
        
        Args:
            width (int): The width of the basis functions.
            
        Returns:
            RaisedCosineBasis: The object itself, with a defined :paramref:`basis` attribute.
        """
        self.width = width
        self.t = np.arange(width)
        rev = -1 if self.reversed_ else 1
        self.basis = [
            make_weakref(
                self.get_raised_cosine(
                    self.a,
                    self.c,
                    phi,
                    self.t,
                    backend=self.backend)[1][::rev])
            for phi in self.phis
        ]
        return self


    def get(self):
        """Get the basis functions :math:`\mathbf{f}`.
        
        Returns:
            list: The list of basis functions."""
        return self.basis


    def get_superposition(self, x):
        """Get the weighed sum :math:`\mathbf{w}(\\tau)` of the basis functions :math:`f`.
        
        The superposition of all basis functions, weighed by the input weights,
        is a single filter of length :paramref:`width` that can be used to weigh the input data: synapse activations.
        
        .. math::
    
            \mathbf{w}(\\tau) = \sum_{i} x_i\ f_i(\\tau) = \mathbf{x} \cdot \mathbf{f}(\\tau)
        
        Args:
            x (array): The (learnable) input weights :math:`\mathbf{x}`
        
        Returns:
            array: The weighed sum of the basis functions.
        """
        return sum([b_i * x_i for b_i, x_i in zip(self.basis, x)])


    def visualize(self, ax=None, plot_kwargs=None):
        """Visualize the basis functions :math:`\mathbf{f}`.
        
        Args:
            ax (plt.axis): The axis to plot on. Default is ``None``.
            plot_kwargs (dict): The plot arguments. Default is ``None``.
            
        Returns:
            plt.axis: The axis with the plot.
        """
        if plot_kwargs is None:
            plot_kwargs = {}
        if ax is None:
            ax = plt.figure().add_subplot(111)
        for b in self.get():
            ax.plot(self.t, b, **plot_kwargs)


    def visualize_w(self, x, ax=None, plot_kwargs=None):    
        r"""Visualize the superposition :math:`\mathbf{w}(\tau)` of the basis functions :math:`\mathbf{f}`.
        
        Args:
            x (array): The (learnable) input weights for the basis functions.
            ax (plt.axis): The axis to plot on. Default is ``None``.
            plot_kwargs (dict): The plot arguments. Default is ``None``.
        """
        if plot_kwargs is None:
            plot_kwargs = {}
        if ax is None:
            ax = plt.figure().add_subplot(111)
        ax.plot(self.t, self.get_superposition(x), **plot_kwargs)


    @staticmethod
    def get_raised_cosine(
        a=1,
        c=1,
        phi=0,
        t=None,
        backend=np):
        """Calculate a single raised cosine basis function :math:`f_i` over the domain :math:`t`.
        
        Args:
            a (float): The steepness of the raised cosine. Default is :math:`1`.
            c (float): The offset of the raised cosine. Default is :math:`1`.
            phi (float): The phase of the raised cosine. Default is :math:`0`.
            t (array): The domain of the raised cosine. Default is :math:`[0, 80]`.
            backend (module): The backend to use (cupy or numpy). Default is ``numpy``.
            
        Returns:
            tuple: The domain :math:`t` and the raised cosine basis function :math:`f_i` over this domain.
        """
        t = t if t is not None else np.arange(0, 80, 1)
        cos_arg = a * np.log(t + c) - phi
        v = .5 * np.cos(cos_arg) + .5
        v[cos_arg >= np.pi] = 0
        v[cos_arg <= -np.pi] = 0
        return backend.array(t.astype('f4')), backend.array(v.astype('f4'))


class Strategy_ISIraisedCosine(_Strategy):
    """:skip-doc:"""
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
        self._get_score = partial(self._get_score_static, self.RaisedCosineBasis_postspike, self.ISI)

    def _get_x0(self):
        """Get an initial guess for the learnable weights of the basis functions :math:`\mathbf{x}`.
        
        These weights are optimized by the solver.
        
        See also:
            :math:`x_i` in :py:class:`~simrun.modular_reduced_model_inference.RaisedCosineBasis`
            
        See also:
            :py:mod:`simrun.modular_reduced_model_inference.solver` for the optimization process.
        
        Returns:
            np.array: An array of random values in the range :math:`[-5, 5)`, with the same length as the basis parameters.
        """
        basis_dimension = len(self.RaisedCosineBasis_postspike.phis)
        return (np.random.rand(basis_dimension) * 2 - 1) * 5

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


class Strategy_spatiotemporalRaisedCosine(_Strategy):
    r'''Spatiotemporal raised cosine strategy.
    
    Uses the :py:class:``RaisedCosineBasis`` to create a set of basis functions.
    
    Attention:
        The input data must contain the following keys:
        - ``spatiotemporalSa``: The spatiotemporal synaptic activation patterns of shape (n_spatial_bins, n_temporal_bins, n_trials).
        - ``st``: The spike times.
        - ``y``: The labels.
        - ``ISI``: The inter-spike intervals.

    Attributes:
        RaisedCosineBasis_spatial (RaisedCosineBasis): The spatial basis functions :math:`\mathbf{g}(z)`.
        RaisedCosineBasis_temporal (RaisedCosineBasis): The temporal basis functions :math:`\mathbf{f}(t)`.
        base_vectors_arrays_dict (dict): 
            The basis vectors for each group. basis vectors are of shape (n_trials, N_{\tau}, N_{z})
            These basis vectors are used for the optimizer, and are already multiplied with the data.
            Do not confuse them with the basis vectors of :paramref:`RaisedCosineBasis_spatial` and :paramref:`RaisedCosineBasis_temporal`,
            as the latter are not multiplied with the synapse activaiton data.
        groups (list): The list of groups. Usually simply ``['EXC', 'INH']``.
        len_z (int): The length of the spatial domain i.e. the amount of spatial basis vectors.
        len_t (int): The length of the temporal domain i.e. the amount of temporal basis vectors.
        len_trials (int): The number of trials.
        convert_x (callable): The conversion function to convert the 1D learnable weight vector :math:`\mathbf{x}` into a structured dictionary.
        _get_score (callable): The cost function to provide to the optimizer.
    '''

    def __init__(self, name, RaisedCosineBasis_spatial, RaisedCosineBasis_temporal):
        """
        Args:
            name (str): The name of the strategy.
            RaisedCosineBasis_spatial (RaisedCosineBasis): The spatial basis functions :math:`\mathbf{g}(z)`.
            RaisedCosineBasis_temporal (RaisedCosineBasis): The temporal basis :math:`\mathbf{f}(t)`.
        """
        super(Strategy_spatiotemporalRaisedCosine, self).__init__(name)
        self.RaisedCosineBasis_spatial = RaisedCosineBasis_spatial
        self.RaisedCosineBasis_temporal = RaisedCosineBasis_temporal

    def _setup(self):
        """Compute the strategy's basis vectors and set up the objective function.
        """
        self.compute_basis()
        self.groups = sorted(self.base_vectors_arrays_dict.keys())
        self.len_z, self.len_t, self.len_trials = self.base_vectors_arrays_dict.values()[0].shape
        self.convert_x = partial(self._convert_x_static, self.groups, self.len_z)
        self._get_score = partial(self._get_score_static, self.convert_x, self.base_vectors_arrays_dict)

    def compute_basis(self):
        r'''Compute the basis vectors for the dataset.
        
        These basis vectors are defined as :math:`\mathbf{f}(t) \cdot \mathbf{g}(z) \cdot \mathbf{D}`.
        When these basis vectors are weighed, they form the argument of the integral over the domain.
        Once integrated over the domain, they yield the weighted net input.
        
        .. math::

            WNI(t) = \int_{t-width}^{t} \int_z \mathbf{w}_{\\tau}(\\tau) \cdot \mathbf{w}_{z}(z) \cdot \mathbf{D} = \int_{t-width}^{t} \int_z \mathbf{x} \cdot \mathbf{y} \cdot \mathbf{f}(t) \cdot \mathbf{g}(z) \cdot \mathbf{D}
        
        Attention:
            These are not the same basis vectors as in :py:class:`RaisedCosineBasis`.
            These basis vectors are already multiplied with the data :math:`\mathbf{D}`.
            Since dot product is commutative, the order of this multiplication does not matter for calculating
            the weighted net input, but these intermediate basis vectors are different.
            
        Returns:
            dict: A dictionary of basis vectors for each group. basis vectors are of shape :math:`(n_trials, dim(\mathbf{f}(\\tau)), dim(\mathbf{g}(z)))`.
        '''
        
        def _compute_base_vector_array(spatiotemp_SA):
            r"""
            Args:
                spatiotemp_SA (array): The spatiotemporal synaptic activation patterns of shape :math:`(n_trials, dim(\mathbf{f}(\\tau)), dim(\mathbf{g}(z)))`.
                
            Returns:
                array: The basis vector array of shape :math:`(n_trials, dim(\mathbf{f}(\\tau)), dim(\mathbf{g}(z)))`.
            """
            _, time_domain, space_domain = spatiotemp_SA.shape
            self.RaisedCosineBasis_spatial.compute(space_domain)
            self.RaisedCosineBasis_temporal.compute(time_domain)
            spatial_basis_functions = self.RaisedCosineBasis_spatial.get()  # len(x) x domain
            temporal_basis_functions = self.RaisedCosineBasis_temporal.get()
            base_vector_array = []
            for f_z_i in spatial_basis_functions:
                base_vector_row = []
                for f_t_i in temporal_basis_functions:
                    base_vector_row.append(np.dot(np.dot(spatiotemp_SA, f_z_i), f_t_i))
                base_vector_array.append(base_vector_row)
            return np.array(base_vector_array).astype('f4')

        base_vectors_arrays_dict = {}
        for group, spatiotemp_SA in self.data['spatiotemporalSa'].iteritems():
            base_vector_array = _compute_base_vector_array(spatiotemp_SA)
            base_vectors_arrays_dict[group] = make_weakref(np.array(np.array(base_vector_array).astype('f4')))
        self.base_vectors_arrays_dict = base_vectors_arrays_dict

    def _get_x0(self):
        r"""Get an initial guess for the learnable weights  :math:`\mathbf{x}` and :math:`\mathbf{y}` of the basis functions :math:`\mathbf{f}(\tau)` and :math:`\mathbf{g}(z)`.
        
        Returns:
            np.array: An array of random values in the range :math:`[-1, 1)`, with the same length as the basis parameters.
        """
        return np.random.rand((self.len_z + self.len_t) * len(self.groups)) * 2 - 1

    @staticmethod
    def _convert_x_static(groups, len_z, x):
        """Convert the input array :math:`\mathbf{x}` into a dictionary of basis vectors.
        
        Useful for passing the learnable weights to the optimizer as a one-dimensional array,
        but keeping track of the basis vectors for each group and dimension.
        
        Args:
            groups (list): The list of groups.
            len_z (int): The length of the spatial domain.
            x (array): The one-dimensional input array.
            
        Returns:
            dict: A dictionary of basis vectors for each group.
            
        Example:

            >>> x
            array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.])
            >>> groups
            ['EXC', 'INH']
            >>> len_z
            3                               # implies len_t is len(x)/2 - len_z = 2
            >>> _convert_x_static(groups, len_z, x)
            {
                'EXC': (
                    array([0.1, 0.2, 0.3]), # spatial
                    array([0.4, 0.5])),     # temporal
                'INH': (
                    array([0.6, 0.7, 0.8]), # spatial
                    array([0.9, 1.]))}      # temporal
            
        """
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
        r"""Calculate the weighted net input :math:`WNI(t)` for the given weights :math:`\mathbf{x}`.
        
        This is the method that calculates the cost function for the optimizer.
        It is assigned to :py:meth:`~simrun.modular_reduced_model_inference.Strategy_spatiotemporalRaisedCosine._get_score` during
        the setup of the strategy.
        
        This method left-multiplies the basis vectors :math:`\mathbf{f}(\tau) \cdot \mathbf{g}(z) \cdot \mathbf{D}` 
        with the learnable weights :math:`\mathbf{x}` and :math:`\mathbf{y}`.
        It then integrates the results for each group to get the weighted net input :math:`WNI(t)`.
        
        Args:
            convert_x (callable): The conversion function from the learnable weights to the basis vectors.
            base_vectors_arrays_dict (dict): The dictionary of basis vectors for each group.
            x (array): 
                The learnable weights :math:`\mathbf{x}` and :math:`\mathbf{y}` as a single array.
                These are converted to spatial and temporal weights per group with :paramref:`convert_x`.
            
        Attention:
            These basis vectors are already multiplied with the data, and are thus not the same
            as the basis vectors in :py:class:`RaisedCosineBasis`.
            Since dot product is commutative, the order of this multiplication does not matter.
            
        Returns:
            array: The weighted net input :math:`WNI(t)` of length ``n_trials``.
        """
        outs = []
        for group, (x_z, x_t) in convert_x(x).iteritems():
            array = base_vectors_arrays_dict[group]  # shape: (len_z, len_t, n_trials)
            time_weighed_input = np.dot(dereference(x_t), dereference(array)).squeeze()
            spacetime_weighed_input = np.dot(dereference(x_z), dereference(time_weighed_input)).squeeze()
            outs.append(spacetime_weighed_input)
        wni = np.vstack(outs).sum(axis=0)
        return wni  # shape: (n_trials,)

    def normalize(self, x, flipkey=None):
        '''Normalize the kernel basis functions such that sum of all absolute values of all kernels is 1.
        
        Attention:
            These are the same basis functions as in :py:class:`RaisedCosineBasis`.
            These are thus not multiplied with the synapse activation data, as is the case with :py:meth:`compute_basis`
            
        Args:
            x (array): The learnable weights :math:`\mathbf{x}` and :math:`\mathbf{y}` as a 1D array.
                These are converted to spatial and temporal weights per group with :paramref:`convert_x`.
            
        Returns:
            array: The normalized learnable weights :math:`\mathbf{x}`.
        '''
        x = self.convert_x(x)
        #temporal
        b = self.RaisedCosineBasis_temporal
        x_exc_t = x[('EXC',)][1]
        x_inh_t = x[('INH',)][1]
        x_exc_z = x[('EXC',)][0]
        x_inh_z = x[('INH',)][0]
        norm_exc = b.get_superposition(x_exc_t)[np.argmax(np.abs(b.get_superposition(x_exc_t)))]
        norm_inh = -1 * b.get_superposition(x_inh_t)[np.argmax(np.abs(b.get_superposition(x_inh_t)))]
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
        """Map groups to a color.
        
        Currently, only 'EXC' and 'INH' are mapped to red and grey, respectively.
        
        Args:
            group (str): The group to map to a color.
            
        Returns:
            str: The color of the group.
        """
        if 'EXC' in group:
            return 'r'
        elif 'INH' in group:
            return 'grey'
        else:
            return None

    def visualize(
        self,
        optimizer_output,
        only_successful=False,
        normalize=True):
        """Plot the basis functions.
        
        Attention:
            These are the same basis functions as in :py:class:`RaisedCosineBasis`.
            These are thus not multiplied with the synapse activation data, as is the case with :paramref:`basis`.
            
        Args:
            optimizer_output (List[scipy.optimize.OptimizeResult]): An array of optimizer outputs. usually one element per data split.
            only_succesful (bool): Whether to only plot the successful optimizer outputs. Default is ``False``.
            normalize (bool): Whether to normalize the basis functions. Default is ``True``.
            
        Returns:
            None: Nothing. Plots the basis functions.
        """
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
                self.RaisedCosineBasis_spatial.visualize_x(
                    x_z,
                    ax=ax_z,
                    plot_kwargs={'c': c})


class Strategy_temporalRaisedCosine_spatial_cutoff(_Strategy):
    '''requires keys: temporalSa, st, y, ISI
    
    :skip-doc:
    '''

    def __init__(
        self, 
        name, 
        RaisedCosineBasis_spatial,
        RaisedCosineBasis_temporal):
        super(Strategy_spatiotemporalRaisedCosine, self).__init__(name)
        self.RaisedCosineBasis_spatial = RaisedCosineBasis_spatial
        self.RaisedCosineBasis_temporal = RaisedCosineBasis_temporal

    def _setup(self):
        self.compute_basis()
        self.groups = sorted(self.base_vectors_arrays_dict.keys())
        self.len_z, self.len_t, self.len_trials = self.base_vectors_arrays_dict.values()[0].shape
        self.convert_x = partial(self._convert_x_static, self.groups, self.len_z)
        self._get_score = partial(self._get_score_static, self.convert_x, self.base_vectors_arrays_dict)

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
                tSa = np.dot(stSa, z).squeeze()
                for t in self.RaisedCosineBasis_temporal.compute(len_t).get():
                    base_vector_row.append(np.dot(tSa, t))
                base_vector_array.append(base_vector_row)
            base_vectors_arrays_dict[group] = make_weakref(
                np.array(np.array(base_vector_array).astype('f4')))
        self.base_vectors_arrays_dict = base_vectors_arrays_dict

    def _get_x0(self):
        return np.random.rand((self.len_z + self.len_t) * len(self.groups)) * 2 - 1

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
        
        # temporal
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


class Strategy_linearCombinationOfData(_Strategy):
    """:skip-doc:"""
    def __init__(self, name, data_keys):
        super(Strategy_linearCombinationOfData, self).__init__(name)
        self.data_keys = data_keys
        self.data_values = None

    def _setup(self):
        self.data_values = np.array([self.data[k] for k in self.data_keys])
        self._get_score = partial(self._get_score_static, self.data_values)

    def _get_x0(self):
        return np.random.rand(len(self.data_keys)) * 2 - 1

    @staticmethod
    def _get_score_static(data_values, x):
        return np.dot(data_values.T, x)


class CombineStrategies_sum(_Strategy):
    """Combine multiple strategies by summing together their cost function.
    
    
    :skip-doc:"""
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
        self._get_score = partial(
            self._get_score_static, 
            score_functions,
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
        return np.concatenate(out)
