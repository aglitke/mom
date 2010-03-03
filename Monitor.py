import threading
from collections import deque
from Collectors import Collector
from Entity import Entity
from MomUtils import *

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
        self.ready = False
        
    def collect(self):
        """
        Collect a set of statistics by invoking all defined collectors and
        merging the data into one dictionary and pushing it onto the deque of
        historical statistics.  Maintain a history length as specified in the
        config file.
        Return: The dictionary of collected statistics
        """
        data = {}
        try:
            for c in self.collectors:
                data.update(c.collect())
        except Collector.CollectionError as e:
            logger(LOG_DEBUG, "Collection error: %s", e.message)
            self.ready = False
            return None

        with self.data_sem:
            self.statistics.append(data)
            if len(self.statistics) > self.config.getint('main', 'sample-history-length'):
                self.statistics.popleft()
        self.ready = True
        return data

    def interrogate(self):
        """
        Take a snapshot of this Monitor object and return an Entity object which
        is useful for rules processing.
        Return: A new Entity object
        """
        if self.ready is False:
            return None
        ret = Entity()
        with self.data_sem:
            for prop in self.properties.keys():
                ret._set_property(prop, self.properties[prop])
            ret._set_statistics(self.statistics)
        ret._finalize()
        return ret
