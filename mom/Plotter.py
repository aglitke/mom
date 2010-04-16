import time
import ConfigParser
import logging

class Plotter:
    def __init__(self, plot_dir, name):
        self.file = None
        if plot_dir == '':
            return
        filename = "%s/%s.dat" % (plot_dir, name)
        try:
            self.file = open(filename, 'a')
        except IOError, (errno, str):
            logger = logging.getLogger('mom.Plotter')
            logger.warn("Cannot open plot file %s: %s" , filename, str)

    def __del__(self):
        if self.file is not None:
            self.file.close()
            
    def setFields(self, fields):
        if self.file is None:
            return
        self.keys = list(fields)
        self.keys.sort()
        header = '# time\t ' + '\t '.join(map(str, self.keys)) + '\n'
        self.file.write(header)
        
    def plot(self, data):
        if self.file is None:
            return
        time_val = str(time.time())
        f = lambda x: str(data[x])
        try:
            data_str = time_val + '\t' + '\t'.join(map(f, self.keys)) + '\n'
        except KeyError:
            data_str = "# %s Incomplete data set\n" % time_val
        self.file.write(data_str)
        self.file.flush()
