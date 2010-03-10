import time
import ConfigParser
from MomUtils import *

class Plotter:
    def __init__(self, plot_dir, name):
        self.file = None
        if plot_dir == '':
            return
        filename = "%s/%s.dat" % (plot_dir, name)
        try:
            self.file = open(filename, 'a')
        except IOError as (errno, str):
            logger(LOG_WARN, "Cannot open plot file %s: %s" , filename, str)
        self.write_header = True

    def __del__(self):
        if self.file is not None:
            self.file.close()

    def plot(self, data):
        if self.file is None:
            return
        if self.write_header:
            self.write_header = False
            self.keys = data.keys().sort()
            header = '# time\t ' + '\t'.join(map(str, self.keys)) + '\n'
            self.file.write(header)
        time_val = str(time.time())
        f = lambda x: str(data[x])
        try:
            data_str = time_val + '\t' + '\t'.join(map(f, self.keys)) + '\n'
        except KeyError:
            data_str = "# %s Incomplete data set\n" % time_val
        self.file.write(data_str)
        self.file.flush()
