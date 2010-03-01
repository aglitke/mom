# MomUtils - Program-wide utility functions

(LOG_ERROR, LOG_WARN, LOG_INFO, LOG_DEBUG) = (4, 3, 2, 1)
def logger(level, fmt, *args):
    """
    A completely feature-less logging facility that can be easily extended to
    support verbosity levels and writing to log files.
    """
    if level in (LOG_ERROR, LOG_WARN, LOG_INFO, LOG_DEBUG):
        print fmt % args
