import sys
import os

from ._version import get_versions

class Versions_cached:
    def __init__(self):
        if 'ISF_MINIMIZE_IO' in os.environ:
            print('ISF_MINIMIZE_IO mode')
            self._git_version = 'ISF_MINIMIZE_IO_mode'
            self._conda_list = 'ISF_MINIMIZE_IO_mode'
            self._module_version = {}
            self._hostname = 'ISF_MINIMIZE_IO_mode'
        else:
            self._git_version = None
            self._conda_list = None
            self._module_version = None
            self._hostname = None
    
    @staticmethod
    def _get_module_versions():
        out = {}
        for x in list(sys.modules.keys()):
            if not '.' in x:
                try:
                    out[x] = sys.modules[x].__version__
                except:
                    pass
        return out

    @staticmethod
    def _get_conda_list():
        '''returns conda list, empty string if conda list is not defined'''
        return os.popen("conda list").read()
    
    @staticmethod
    def _get_git_version():
        return get_versions()
    
    def get_module_versions(self):
        if self._module_version is None:
            self._module_version = self._get_module_versions()
        return self._module_version
    
    def get_conda_list(self):
        if self._conda_list is None:
            self._conda_list = self._get_conda_list()
        return self._conda_list
    
    def get_git_version(self):
        if self._git_version is None:
            self._git_version = self._get_git_version()
        return self._git_version
    
    @staticmethod
    def _get_hostname():
        return os.popen("hostname").read()
    
    def get_hostname(self):
        if not self._hostname:
            self._hostname = self._get_hostname()
        return self._hostname
    
    @staticmethod
    def get_history():
        import IPython
        ipython = IPython.get_ipython()
        if ipython is not None:
            out = []
            for l in ipython.history_manager.get_range(0, output = False):
                out.append(l[2])
            return '\n'.join(out)        

    # Use __getstate__ and __setstate__ to make sure, this object does not store any data when it is serialized.
    # This ensures that the module is run at least once per process 
    def __getstate__(self):
        return {}
    
    def __setstate__(self):
        self.__init__()
        
version_cached = Versions_cached()