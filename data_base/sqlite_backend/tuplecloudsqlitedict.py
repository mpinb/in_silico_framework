# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
