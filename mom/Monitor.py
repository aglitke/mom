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
        self.collectors = []
        self.logger = logging.getLogger('mom.Monitor')
        
        plot_dir = config.get('main', 'plot-subdir')
        if plot_dir != '':
            self.plotter = Plotter(plot_dir, name)
        else:
            self.plotter = None
        
        self.ready = False
        self.terminate = False
        
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
        data = {}
        try:
            for c in self.collectors:
                for (key, val) in c.collect().items():
                    if key not in data:
                        data[key] = val
        except Collector.CollectionError as e:
            self.logger.debug("Collection error: %s", e.message)
            self.ready = False
            return None
        except Collector.FatalError as e:
            self.logger.error("Fatal Collector error: %s", e.message)
            self.ready = False
            self.terminate = True
            return None

        with self.data_sem:
            self.statistics.append(data)
            if len(self.statistics) > self.config.getint('main', 'sample-history-length'):
                self.statistics.popleft()
        self.ready = True
        
        if self.plotter is not None:
            self.plotter.plot(data)
        
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
        
    def _should_run(self):
        """
        Private helper to determine if the Monitor should continue to run.
        """
        if self.config.getint('main', 'running') == 1 and not self.terminate:
            return True
        else:
            return False
