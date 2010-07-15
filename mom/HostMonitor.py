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
import time
import logging
from mom.Monitor import Monitor
from mom.Collectors import Collector
from mom.Plotter import Plotter

class HostMonitor(Monitor, threading.Thread):
    """
    The Host Monitor thread collects and reports statistics about the host.
    """
    def __init__(self, config):
        threading.Thread.__init__(self, name="HostMonitor")
        Monitor.__init__(self, config, self.getName())
        self.setDaemon(True)
        self.config = config
        self.logger = logging.getLogger('mom.HostMonitor')
        collector_list = self.config.get('host', 'collectors')
        self.collectors = Collector.get_collectors(collector_list,
                            self.properties)
        if self.collectors is None:
            self.logger.error("Host Monitor initialization failed")
            return
        self.start()

    def run(self):
        self.logger.info("Host Monitor starting")
        interval = self.config.getint('main', 'host-monitor-interval')
        while self._should_run():
            data = self.collect()
            time.sleep(interval)
        self.logger.info("Host Monitor ending")
        
