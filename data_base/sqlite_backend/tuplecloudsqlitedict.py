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
''''
This extends the cloudsqlitedict module to support tuples of strings as keys.
Currently, this comes at the cost, that '@' in keys is not allowed anymore.

The class SqliteDict in this module does not inherit from cloudsqlitedict.SqliteDict,
however it contains an instance of it. In case, some API is missing, simply extend \
this class accordingly.
'''

from . import cloudsqlitedict


def check_key(key):
    if isinstance(key, tuple):
        for k in key:
            if not isinstance(k, str):
                raise ValueError(
                    "keys have to be strings or a tuple of strings")
            if '@' in k:
                raise ValueError(
                    "keys are not allowed to contain the letter '@'")
    elif isinstance(key, str):
        check_key(tuple([key]))
    else:
        raise ValueError("keys have to be strings or a tuple of strings")


def convert_key(key):
    check_key(key)
    if isinstance(key, tuple):
        key = '@'.join(key)
    return key


class SqliteDict(object):

    def __init__(self, basedir, autocommit=False, flag=None):
        self.sqlitedict = cloudsqlitedict.SqliteDict(basedir,
                                                     autocommit=autocommit,
                                                     flag=flag)

    def __setitem__(self, key, value):
        key = convert_key(key)
        self.sqlitedict.__setitem__(key, value)

    def __getitem__(self, key):
        key = convert_key(key)
        return self.sqlitedict.__getitem__(key)

    def __delitem__(self, key):
        key = convert_key(key)
        return self.sqlitedict.__delitem__(key)

    def keys(self):
        list_ = list(self.sqlitedict.keys())  ###
        out = []
        for l in list_:
            if '@' in l:
                out.append(tuple(l.split('@')))
            else:
                out.append(l)
        return out

    def close(self):
        self.sqlitedict.close()
