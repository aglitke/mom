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

import threading
import ConfigParser
import logging
from collections import deque
from mom.Collectors import Collector
from mom.Entity import Entity
from mom.Plotter import Plotter

class Monitor:
    """
    The Monitor class represents an entity, about which, data is collected and
    reported.  Each monitor has a dictionary of properties which are relatively
    static such as a name or ID.  Additionally, statistics are collected over
    time and queued so averages and trends can be analyzed.
    """
    def __init__(self, config, name):
        # Guard the data with a semaphore to ensure consistency.
        self.data_sem = threading.Semaphore()
        self.properties = {}
        self.statistics = deque()
        self.variables = {}
        self.name = name
        self.fields = None
        self.collectors = []
        self.logger = logging.getLogger('mom.Monitor')
        
        plot_dir = config.get('__int__', 'plot-subdir')
        if plot_dir != '':
            self.plotter = Plotter(plot_dir, name)
        else:
            self.plotter = None
        
        self.ready = None 
        self._terminate = False
        
    def collect(self):
        """
        Collect a set of statistics by invoking all defined collectors and
        merging the data into one dictionary and pushing it onto the deque of
        historical statistics.  Maintain a history length as specified in the
        config file.
        
        Note: Priority is given to collectors based on the order that they are
        listed in the config file (ie. if two collectors produce the same
        statistic only the value produced by the first collector will be saved).
        Return: The dictionary of collected statistics
        """
        
        # The first time we are called, populate the list of expected fields
        if self.fields is None:
            self.fields = set()
            for c in self.collectors:
                self.fields |= c.getFields()
            self.logger.debug("Using fields: %s", repr(self.fields))
            if self.plotter is not None:
                self.plotter.setFields(self.fields)
        
        data = {}
        for c in self.collectors:
            try:
                for (key, val) in c.collect().items():
                    if key not in data:
                        data[key] = val
            except Collector.CollectionError, e:
                self._disp_collection_error("Collection error: %s" % e.msg)
            except Collector.FatalError, e:
                self._set_not_ready("Fatal Collector error: %s" % e.msg)
                self.terminate()
                return None
        if set(data) != self.fields:
            self._set_not_ready("Incomplete data: missing %s" % \
                                (self.fields - set(data)))
            return None

        self.data_sem.acquire()
        self.statistics.append(data)
        if len(self.statistics) > self.config.getint('main', 'sample-history-length'):
            self.statistics.popleft()
        self.data_sem.release()
        self._set_ready()
        
        if self.plotter is not None:
            self.plotter.plot(data)
        
        return data

    def interrogate(self):
        """
        Take a snapshot of this Monitor object and return an Entity object which
        is useful for rules processing.
        Return: A new Entity object
        """
        if self.ready is not True:
            return None
        ret = Entity(monitor=self)
        self.data_sem.acquire()
        for prop in self.properties.keys():
            ret._set_property(prop, self.properties[prop])
        for var in self.variables.keys():
            ret._set_variable(var, self.variables[var])
        ret._set_statistics(self.statistics)
        self.data_sem.release()
        ret._finalize()
        return ret

    def update_variables(self, variables):
        """
        Update the variables array to store any updates from an Entity
        """
        self.data_sem.acquire()
        for (var, val) in variables.items():
            self.variables[var] = val
        self.data_sem.release()
        
    def terminate(self):
        """
        Instruct the Monitor to shut down
        """
        self._terminate = True

    def isReady(self):
        """
        Check if all configured Collectors are working properly.
        """
        return bool(self.ready)
        
    def _set_ready(self):
        if self.ready is not True:
            self.logger.info('%s is ready', self.name)
        self.ready = True

    def _disp_collection_error(self, message=None):
        if message is not None:
            if self.ready is False:
                self.logger.debug('%s: %s', self.name, message)
            else: # True or None
                self.logger.warn('%s: %s', self.name, message)

    def _set_not_ready(self, message=None):
        self.ready = False
        self._disp_collection_error(message)

    def _should_run(self):
        """
        Private helper to determine if the Monitor should continue to run.
        """
        if self.config.getint('__int__', 'running') == 1 and not self._terminate:
            return True
        else:
            return False
