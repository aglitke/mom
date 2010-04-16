from mom.Collectors.Collector import *

class GuestQemuProc(Collector):
    """
    This Collector returns host fault statistics for the qemu process
    representing a guest.
        host_minor_faults - The number of host minor faults a guest's qemu
                            process caused since the last collection.
        host_major_faults - The number of host major faults a guest's qemu
                            process caused since the last collection.
    Host major faults generally require host disk IO to satisfy, host minor
    faults do not.
    """
    def __init__(self, properties):
        self.pid = properties['pid']
        self.pid_stat_file = None
        if self.pid is not None:
            self.pid_stat_file = open_datafile("/proc/" + str(self.pid) + "/stat")
        self.prev_minor_faults = None
        self.prev_major_faults = None

    def __del__(self):
        if self.pid_stat_file is not None:
            self.pid_stat_file.close()

    def collect(self):
        if self.pid_stat_file is None:
            return {}

        # Only report the change in these statistics since the last collection
        self.pid_stat_file.seek(0)
        stats = self.pid_stat_file.read().split()
        cur_minor_faults = int(stats[9])
        cur_major_faults = int(stats[11])
        if self.prev_minor_faults is None:
            self.prev_minor_faults = cur_minor_faults
        if self.prev_major_faults is None:
            self.prev_major_faults = cur_major_faults
        minor_faults = cur_minor_faults - self.prev_minor_faults
        self.prev_minor_faults = cur_minor_faults
        major_faults = cur_major_faults - self.prev_major_faults
        self.prev_major_faults = cur_major_faults

        return { 'host_minor_faults': minor_faults, 'host_major_faults': major_faults }
        
    def getFields(self=None):
        return set(['host_minor_faults', 'host_major_faults'])

def instance(properties):
    return GuestQemuProc(properties)
