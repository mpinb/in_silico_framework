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
""":py:mod:`data_base` specific exceptions.
"""

class DataBaseException(Exception):
    '''Typical data_base errors'''
    pass

class ModelDataBaseException(DataBaseException):
    '''Typical model_data_base errors
    
    :skip-doc:'''
    pass

class ISFDataBaseException(DataBaseException):
    '''Typical isf_data_base errors'''
    pass


class DataBaseWarning(Warning):
    """Warnings are usually handled by the logger. However, if you want to raise a warning, you can use this class.
    
    :skip-doc:
    """
    def __init__(self, message):
        self.message = message
        
    def __str__(self):
        return repr(self.message)
