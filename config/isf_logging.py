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
"""Set up logging for ISF."""
import logging, sys, warnings, os
from contextlib import contextmanager

@contextmanager
def stream_to_logger(logger, level=None):
    """
    Wrapper for a stream object that redirects writes to a logger instance.
    Can be used as a context manager::

        >>> with StreamToLogger(logger, logging.INFO) as sys.stdout:
        >>>    do_something()
    
    Used for reading in :ref:`hoc_file_format` files that provide output due to various print statements in the `.hoc` file, or capturing NEURON output.
    """
    class StreamToLogger:
        def __init__(self, logger, level):
            self.logger = logger
            self.level = level
            self.linebuf = ''

        def write(self, buf):
            for line in buf.rstrip().splitlines():
                self.logger.log(self.level, line.rstrip())

        def flush(self):
            pass

    stdout = sys.stdout
    stderr = sys.stderr
    sys.stdout = StreamToLogger(logger, level if level else logging.INFO)
    sys.stderr = StreamToLogger(logger, logging.ERROR)
    try:
        yield
    finally:
        sys.stdout = stdout
        sys.stderr = stderr


class LastPartFilter(logging.Filter):
    """
    Logging add-on that adds a field ``name_last`` that only shows the last part of the module or file name.
    Useful for logger stream handlers, when the logger name can be quite long and muddles output.
    """
    def filter(self, record):
        # remove ISF prefix from parent logger to find origin of log
        record_origin = ".".join(record.name.split('.')[1:])
        if os.path.exists(record_origin):
            # logging gets a filename
            split_char = os.sep
        else:
            # logging gets a FQN
            split_char = '.'
        record.name_last = record.name.split(split_char)[-1]
        return True
    

class RecordFilter(logging.Filter):
    """
    Logging add-on that filters out logs if they contain a certain string.
    """
    def __init__(self, filter_string):
        super().__init__()
        self.filter_string = filter_string
    
    def filter(self, record):
        if self.filter_string in record.name:
            return False
        return True


def add_logging_level(levelName, levelNum, methodName=None):
    """
    Comprehensively adds a new logging level to the ``logging`` module and the
    currently configured logging class.

    ``levelName`` becomes an attribute of the ``logging`` module with the value
    ``levelNum``. `methodName` becomes a convenience method for both ``logging``
    itself and the class returned by `logging.getLoggerClass()` (usually just
    ``logging.Logger``). If ``methodName`` is not specified, ``levelName.lower()`` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present 

    Example:
    
        >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
        >>> logging.getLogger(__name__).setLevel("TRACE")
        >>> logging.getLogger(__name__).trace('that worked')
        >>> logging.trace('so did this')
        >>> logging.TRACE
        5

    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
       raise AttributeError('{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
       raise AttributeError('{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
       raise AttributeError('{} already defined in logger class'.format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)
    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)

# All loggers will inherit the root logger's level and handlers
root_logger = logging.getLogger()
isf_logger = root_logger.getChild("ISF")

# Redirect warnings to the logging system. This will format them accordingly.
logging.captureWarnings(True)
warnings.showwarning = lambda message, category, filename, lineno, f=None, line=None: \
    isf_logger.getChild(filename).warning(message)

# Stream handler: where to redirect the logs to
logger_stream_handler = logging.StreamHandler(stream=sys.stdout)
logger_stream_handler.name = "ISF_logger_stream_handler"
logger_stream_handler.setFormatter(logging.Formatter("[%(levelname)s] %(name_last)s: %(message)s"))
root_logger.addHandler(logger_stream_handler)

# Filters
logger_stream_handler.addFilter(LastPartFilter())

# Add custom logging levels
add_logging_level("ATTENTION", logging.WARNING - 5)

# initialize with INFO level
isf_logger.setLevel(logging.INFO)
logger = isf_logger