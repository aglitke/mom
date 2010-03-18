from Monitor import Monitor
from Collectors import Collector
import threading
import ConfigParser
import time
from MomUtils import *
from Plotter import Plotter

class HostMonitor(Monitor, threading.Thread):
    """
    The Host Monitor thread collects and reports statistics about the host.
    """
    def __init__(self, config):
        threading.Thread.__init__(self, name="HostMonitor")
        Monitor.__init__(self, config, self.name)
        self.daemon = True
        self.config = config
        collector_list = self.config.get('host', 'collectors')
        self.collectors = Collector.get_collectors(collector_list,
                            self.properties)
        if self.collectors is None:
            logger (LOG_ERROR, "Host Monitor initialization failed")
            return
        self.start()

    def run(self):
        logger(LOG_INFO, "Host Monitor starting")
        interval = self.config.getint('main', 'host-monitor-interval')
        while self._should_run():
            data = self.collect()
            time.sleep(interval)
        logger(LOG_INFO, "Host Monitor ending")
        
