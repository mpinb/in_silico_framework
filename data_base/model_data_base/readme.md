# ModelDataBase

ModelDataBase is the data management system originally devised to store data in the IBS group, authored by Arco Bast. 
Mostly due to the deprecation of the pandas_msgpack format and issues with Pickle, it has been rewritten into the general [data_base](../__init__.py) package, which uses the subpackage [data_base.isf_data_base](data_base.isf_data_base) by default.

The ModelDataBase subpackage is kept around for compatibility with old data of the IBS group at MPINB, Bonn. It should not be used by anyone else.