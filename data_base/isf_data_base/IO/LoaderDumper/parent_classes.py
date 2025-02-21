"""Base class for child Loader classes

This module provides a base class, to be used as a template for all child classes.
Every Loader class in the :py:mod:`data_base.isf_data_base.IO.LoaderDumper` package inherits from this class.
"""


class Loader:
    """Base class for child Loader classes"""

    def repair(self):
        """:skip-doc:"""
        raise NotImplementedError