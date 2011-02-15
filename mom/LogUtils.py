# Memory Overcommitment Manager
# Copyright (C) 2011 Adam Litke, IBM Corporation
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

import logging

def log_set_verbosity(logger, verbosity):
    if verbosity == '5' or verbosity == 'debug':
        level = logging.DEBUG
    elif verbosity == '4' or verbosity == 'info':
        level = logging.INFO
    elif verbosity == '3' or verbosity == 'warn':
        level = logging.WARN
    elif verbosity == '2' or verbosity == 'error':
        level = logging.ERROR
    elif verbosity == '1' or verbosity == 'critical':
        level = logging.CRITICAL
    else:
        level = logging.DEBUG
    logger.setLevel(level)   
    return level 
