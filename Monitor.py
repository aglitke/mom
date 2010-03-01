import threading
from collections import deque
import Collectors.Collector

class Monitor:
    """
    The Monitor class represents an entity, about which, data is collected and
    reported.  Each monitor has a dictionary of properties which are relatively
    static such as a name or ID.  Additionally, statistics are collected over
    time and queued so averages and trends can be analyzed.
    """
    def __init__(self):
        # Guard the data with a semaphore to ensure consistency.
        self.data_sem = threading.Semaphore()
        self.properties = {}
        self.statistics = deque()
        self.collectors = []
        
    def collect(self):
        """
        Collect a set of statistics by invoking all defined collectors and
        merging the data into one dictionary and pushing it onto the deque of
        historical statistics.  Maintain a history length as specified in the
        config file.
        Return: The dictionary of collected statistics
        """
        data = {}
        for c in self.collectors:
            data.update(c.collect())

        with self.data_sem:
            self.statistics.append(data)
            if len(self.statistics) > self.config.getint('main', 'sample-history-length'):
                self.statistics.popleft()
        self.ready = True
        return data



