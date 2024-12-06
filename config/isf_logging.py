"""Set up logging for ISF."""
import logging, sys

class LastPartFilter(logging.Filter):
    """
    Logging add-on that adds a field that only shows the last part of the module name.
    Useful for logger stream handlers, when the logger name can be quite long and muddles output.
    """
    def filter(self, record):
        record.name_last = record.name.rsplit('.', 1)[-1]
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
logger_stream_handler = logging.StreamHandler(stream=sys.stdout)
logger_stream_handler.name = "ISF_logger_stream_handler"
logger_stream_handler.setFormatter(
    logging.Formatter("[%(levelname)s] %(name_last)s: %(message)s"))
logger_stream_handler.addFilter(LastPartFilter())
root_logger.handlers = [logger_stream_handler]
isf_logger.setLevel(logging.INFO)  # Set back to WARNING at the end

add_logging_level("ATTENTION", logging.WARNING - 5)

logger = isf_logger