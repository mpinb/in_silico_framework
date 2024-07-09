import pandas as pd
from collections.abc import Sequence
import numpy as np

class AbstractDataFrameWrapper(object):
    """
    Baseclass for the DataFrame wrappers.
    This baseclass takes care of everything that the DataFrame wrappers don't have.
    
    All methods or attributes that are not overwritten by specific DataFrame wrappers are passed to the underlying DataFrame instead.

    While it supports dictionary-like __getitem__ and __setitem__ methods, .loc or .iloc are not supported.
    Instead, use the .df attribute to access the underlying DataFrame directly.
    
    """
    def __init__(self, data):
        self.df = data
        self.name = "Abstract DataFrame"

    def __setattr__(self, attr, value):
        if attr in ['df', 'name', 'shape', 'columns']:
            self.__dict__[attr] = value
        else:
            setattr(self.df, attr, value)

    def __setitem__(self, key, value):
        self.df[key] = value

    def __getitem__(self, key):
        return self.df[key]

    def __getattr__(self, attr):
        # I can fetch df from self without infinite recursion
        # because Python first looks if it is in the instance (which it should if it's initialized)
        # before calling __getattr__
        if hasattr(self.df, attr):
            return getattr(self.df, attr)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{attr}', and neither does its underlying dataframe.")

class PandasTableWrapper(AbstractDataFrameWrapper):
    """
    This class serves as a wrapper around the Pandas DataFrame, providing a unified interface for linked views.

    It overrides the 'min', 'max', 'mean', and 'median' methods to support binning.
    If the arguments ['binby', 'shape', 'selection', 'limits'] are not specified, these methods will operate on the undelrying dataframe with no modifications.
    Otherwise, a vaex-like binning operation will be performed on the underlying dataframe, and the result will be returned.

    Added minmax for vaex-consistent API
    """
    def __init__(self, data):
        super().__init__(data)
        self.columns = data.columns.tolist() if isinstance(data, pd.DataFrame) else data.Index

    def binby(self, df, columns, limits, shape):
        """Calculates some statistic on a binned representation of the data. 
        These bins can be N-dimensional, but tend to be 1d, 2D and occasionally 3d, as they are used for plotting.

        Args:
            columns (array): Array of column names to bin by.
            binsize (Sequence): binsize defines the size of the bins, and is of shape Nx2, where N is the number of dimensions.

        Returns:
            pd.DataFrameGroupBy: a pd.DataFrameGroupBy object that cannot be used for PandasTableWrapper
        """
        df = df if df is not None else self.df
        binsizes = get_binsize(shape, limits)
        grouped_df = df.groupby(
            [
                pd.cut(df[col], bins=np.linspace(lim[0], lim[1], shape_+1)) 
                for col, lim, binsize, shape_ in zip(columns, limits, binsizes, shape)
            ])
        return grouped_df

    def calc_like_pandas(self, operation, columns=None):
        if columns is None:
            columns = self.columns
        
        if operation == "minmax":
            filtered_df = self.df[columns].agg(["min", "max"])
        elif operation == "count":
            filtered_df = self.df.count()
        else:
            filtered_df = self.df[columns].agg(operation)
        
        return filtered_df.values

    def calc_binned_statistic(
        self, 
        operation, 
        expression=None, 
        binby=None, 
        shape=None, 
        selection=None, 
        limits=None):
        """
        Creates a binned representation of the data.
        Bins the data on columns ``binby: in a grid of size :arg shape`` and 
        calculates the statistic ``operation: on the column :arg expression``.
        If ``operation: is 'count', then :arg expression`` is redundant and ignored.
        If ``limits`` is passed, the data is clipped to the limits before binning. 

        Args:
            expression (str): The column to compute the statistic on. Not applicable if operation is `count`.
            binby (str): The columns to bin by. Usually 2D
            limits (Sequence): The limits of the binning operation.
            shape (Sequence): The shape of the binning operation.
            operation (str): The statistic to compute. Options are: 'min', 'max', 'mean', 'median', 'count'.

        Returns:
            np.ndarray: a numpy array of shape ``shape`` containing the binned statistic.
        """
        if all([x is None for x in [binby, shape, selection, limits]]):
            return self.calc_like_pandas(operation, columns=expression)

        if limits:
            if not isinstance(limits, Sequence):
                # limits are single int for all columns
                limits = [limits]*len(self.columns)
            assert len(limits) == len(binby), "Got {} limits for {} columns".format(len(limits), len(self.columns))
            assert all([len(limit_pair) == 2 for limit_pair in limits]), "All elements in limits should be  pair of values"
            # clip data to limits
            for col, limit in zip(binby, limits):
                filtered_df = self.df[self.df[col].between(*limit)]

        # create a grouped dataframe       
        grouped_df = self.binby(
            filtered_df.iloc[selection] if selection is not None else filtered_df,  # filter data
            columns=binby, limits=limits, shape=shape  # bin data
            )
        if operation =="minmax":
            r = grouped_df.apply(lambda x: np.array([x.min(), x.max()]))
        elif operation == "count":
            # Counting in bins is done with size() in pandas, not count() (the latter counts for all columns in some 1d bin)
            r = grouped_df.size().unstack()
        else:
            r = getattr(grouped_df[expression], operation)().unstack()
                
        return r.values

    def compute_selection(self, columns, bin_ranges):                
        col1, col2 = columns[0], columns[1]
        mask = None
        for current_bin in bin_ranges: 
            # current_bin is one selected mark/dot in the density plot,
            # i.e., current_bin = [[col1_min, col1_max], [col2_min, col2_max]] 
            current_mask = self.df[col1].between(current_bin[0][0], current_bin[0][1]) & \
                        self.df[col2].between(current_bin[1][0], current_bin[1][1])
            if(mask is None):
                mask = current_mask
            else:
                mask |= current_mask        
        df_selected_indices = self.df.index[mask].to_numpy().astype(int)
        return df_selected_indices
    
    def count(self, *args, **kwargs):
        return self.calc_binned_statistic("count", *args, **kwargs)

    def min(self, *args, **kwargs):
        return self.calc_binned_statistic("min", *args, **kwargs)

    def max(self, *args, **kwargs):
        return self.calc_binned_statistic("max",  *args, **kwargs)

    def mean(self, *args, **kwargs):
        return self.calc_binned_statistic("mean", *args, **kwargs)

    def median(self, *args, **kwargs):
        return self.calc_binned_statistic("median", *args, **kwargs)

    def median_approx(self, *args, **kwargs):
        """Warning: this is same as median for pandas, but not for vaex"""
        return self.calc_binned_statistic("median", *args, **kwargs)
    
    def minmax(self, *args, **kwargs):
        return self.calc_binned_statistic("minmax", *args, **kwargs)

    def to_dict(self, *args, **kwargs):
        """Returns a dictionary representation of the dataframe.
        Orients by records by default, unless otherwise specified.

        Returns:
            dict: The dictionary
        """
        if "orient" not in kwargs:
            kwargs["orient"] = "records"
        return self.df.to_dict(*args, **kwargs)

    def get_selection(self, indices):
        return self.df.iloc[indices]


class VaexTableWrapper(AbstractDataFrameWrapper):
    """
    This class serves as a wrapper around the Vaex DataFrame, providing a unified interface for linked views. 

    It overrides the 'min', 'max', 'mean', and 'median' methods.
    If the 'expression' argument is not specified, these methods will operate on all columns of the DataFrame by default. 

    This modification allows for more intuitive usage and ensures consistent behavior across different views.
    """
    def __init__(self, data):
        super().__init__(data)
        self.columns = self.df.get_column_names()
        self.shape = self.df.shape
    
    def compute_selection(self, columns, bin_ranges, return_indices=True):
        self.df.select_nothing(name="selection_global")
        col1, col2 = columns[0], columns[1]
        for idx, range_i in enumerate(bin_ranges):    
            limit_i = [(range_i[0][0], range_i[0][1]), (range_i[1][0], range_i[1][1])]       
            self.df.select_rectangle(self.df[col1], self.df[col2], limit_i, name="selection_global", mode="or")

        df_selected_indices = self.df.evaluate(self.df["row_index"], selection="selection_global")
        return df_selected_indices.astype(int)

    def calc_binned_statistic(self, operation, *args, **kwargs):
        """
        Creates a binned representation of the data.
        Bins the data on columns ``binby: in a grid of size :arg shape`` and 
        calculates the statistic ``operation: on the column :arg expression``.
        If ``operation: is 'count', then :arg expression`` is redundant and ignored.
        If ``limits`` is passed, the data is clipped to the limits before binning. 

        This is merely a wrapper around the vaex.DataFrame method of the same name, 
        with an additional check if ``expression`` is not specified, the statistic is computed on all columns.

        Args:
            expression (str): The column to compute the statistic on. Not applicable if operation is `count`.
            binby (str): The columns to bin by. Usually 2D
            limits (Sequence): The limits of the binning operation.
            shape (Sequence): The shape of the binning operation.
            operation (str): The statistic to compute. Options are: 'min', 'max', 'mean', 'median', 'count'.

        Returns:
            np.ndarray: a numpy array of shape ``shape`` containing the binned statistic.
        """
        allowed_operations = ["min", "max", "mean", "median_approx", "median", "count"]
        operation = operation if operation != "median" else "median_approx"  # median_approx is vaex's underlying median method
        if operation in allowed_operations:
            if not args and "expression" not in kwargs:
                kwargs["expression"] = self.columns
            operation_func = getattr(self.df, operation)
            return operation_func(*args, **kwargs)
        else:
            raise ValueError(f"Invalid operation. Choose from {allowed_operations}.")

    def min(self, *args, **kwargs):
        return self.calc_binned_statistic("min", *args, **kwargs)

    def max(self, *args, **kwargs):
        return self.calc_binned_statistic("max", *args, **kwargs)

    def mean(self, *args, **kwargs):
        return self.calc_binned_statistic("mean", *args, **kwargs)

    def median_approx(self, *args, **kwargs):
        return self.calc_binned_statistic("median_approx", *args, **kwargs)

    def median(self, *args, **kwargs):
        """compute approx median instead of exact median (faster)"""
        return self.calc_binned_statistic("median_approx", *args, **kwargs)

aggregation_mode_mapping = {
    'mean': lambda x: x.mean,
    'median': lambda x: x.median,
    'min': lambda x: x.min,
    'max': lambda x: x.max,
    'count': lambda x: x.count,
}

def get_binsize_1d(shape, limits):
    binsize = (limits[1] - limits[0])/shape
    return binsize

def get_binsize(shape, limits):
    assert isinstance(shape, Sequence) or isinstance(shape, int), "shape should be an integer or array like"
    if isinstance(shape, int) and isinstance(limits[0], Sequence):
        # limits is nested array implying shape should be array, but shape is scalar
        # vaex supports passing single integer for all columnss
        shape = [shape]*len(limits)
    
    if type(shape) == int:
            return get_binsize_1d(shape, limits)
    else:
        assert len(shape) == len(limits), "Got {} values for shape, but {} limits".format(len(shape, len(limits)))
        assert all([len(limit_pair) == 2 for limit_pair in limits]), "All elements in limits should be  pair of values"
        return [get_binsize_1d(s, l) for s, l in zip(shape, limits)]

def mask_invalid_values(values, operation, mask_value):
    """Given an array of values, masks invalid values as specified by the invalid_values argument.
    What constitutes an invalid value depends on the operation being performed.

    Args:
        values (np.ndarray): Values to mask
        operation (str): Which operation was performed on this set of values. Depending on the operation, different values are considered invalid.
        invalid_value (float | int): Value to use as masking value
    """
    if operation == "count":
        values[values == 0] = mask_value
    elif operation=='max':
        values[values < -10**100] = mask_value
    elif operation=='min':
        values[values > 10**100] = mask_value
    elif operation in ['mean', 'median']:
        pass
    else:
        raise ValueError("Invalid operation. Choose from ['mean', 'median', 'min', 'max', 'count'].")
    values[np.isnan(values)] = mask_value
    return values