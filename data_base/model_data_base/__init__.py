"""
Database system version 1, used by the Oberlaender lab in Bonn.

This has been deprecated in favor of the new database system :py:mod:`data_base.isf_data_base` to keep up to date with
compression formats, and a switch to JSON instead of pickle for metadata and Loader-dumpers.

:skip-doc:
"""

from .model_data_base import ModelDataBase