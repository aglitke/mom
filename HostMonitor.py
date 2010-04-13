from Monitor import Monitor
from Collectors import Collector
import threading
import ConfigParser
import time
import logging
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
        
