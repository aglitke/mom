# Memory Overcommitment Manager
# Copyright (C) 2010 Adam Litke, IBM Corporation
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

import re
import sys
import logging

class Collector:
    """
    Collectors are plugins that return a specific set of data items pertinent to
    a given Monitor object every time their collect() method is called.  Context
    is given by the Monitor properties that are used to init the Collector.
    """
    def __init__(self, properties):
        """
        The Collector constructor should use the passed-in properties to
        establish context from its owning Monitor.
        Override this method when creating new collectors.
        """
        pass
        
    def collect():
        """
        The principle interface for every Collector.  This method is called by a
        monitor to initiate data collection.
        Override this method when creating new collectors.
        Return: A dictionary of statistics.
        """
        return {}
        
    def getFields(self=None):
        """
        Used to query the names of statistics that this Collector will return
        Override this method when creating new collectors.
        Return: A set containing the names of all statistics returned by collect()
        """
        return set()
        
    def instance(properties):
        """
        Override this method when creating new collectors.
        This function is called by Monitor objects to dynamically instantiate a
        set of Collector plugins.
        Return: An instance of this collector initialized with 'properties'
        """
        return Collector(properties)

def get_collectors(config_str, properties):
    """
    Initialize a set of new Collector instances for a Monitor.
    Return: A list of initialized Collectors
    """
    logger = logging.getLogger('mom.Collector')
    collectors = []
    for name in config_str.split(','):
        name = name.lstrip()
        if name == '':
            continue
        try:
            module = __import__('mom.Collectors.' + name, None, None, name)
            collectors.append(module.instance(properties))
        except ImportError:
            logger.warn("Unable to import collector: %s", name)
            return None
        except FatalError, e:
            logger.error("Fatal Collector error: %s", e.msg)
            return None
    return collectors

#
# Collector Exceptions
#
class CollectionError(Exception):
    """
    This exception should be raised if a Collector has a problem during its
    collect() operation and it cannot return a complete, coherent data set.
    """
    def __init__(self, msg):
        self.msg = msg

class FatalError(Exception):
    """
    This exception should be raised if a Collector has a permanent problem that
    will prevent it from initializing or collecting any data.
    """
    def __init__(self, msg):
        self.msg = msg

#
# Collector utility functions
#
def open_datafile(filename):
    """
    Open a data file for reading.
    """
    try:
        filevar = open(filename, 'r')
    except IOError, (errno, strerror):
        logger = logging.getLogger('mom.Collector')
        logger.error("Cannot open %s: %s" % (filename, strerror))
        sys.exit(1)
    return filevar

def parse_int(regex, src):
    """
    Parse a body of text according to the provided regular expression and return
    the first match as an integer.
    """
    m = re.search(regex, src, re.M)
    if m:
        return int(m.group(1))
    else:
        return None
