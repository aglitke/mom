from subprocess import *
from mom.Collectors.Collector import *

class HostKSM(Collector):
    """
    This Collctor returns statistics about the Kernel Samepage Merging daemon
    by reading files in /sys/kernel/vm/ksm/.  The fields provided are:
        ksm_run - Status of the KSM daemon: 0 - Stopped, 1 - Running
        ksm_sleep_millisecs - The amount of idle time between scans (ms)
        ksm_pages_shared - The number of pages being shared
        ksm_pages_sharing - The number of sites where a shared page is in use
        ksm_pages_unshared - The number of pages that are scanned but not shared
        ksm_pages_to_scan - The number of pages to scan in each work interval
        ksm_pages_volatile - The number of pages that are changing too fast to be shared
        ksm_full_scans - The number of times all mergeable memory areas have been scanned
        ksm_shareable - Estimated amount of host memory that is eligible for sharing 
    """
    def __init__(self, properties):
        self.sysfs_keys = [ 'full_scans', 'pages_sharing', 'pages_unshared',
                            'run', 'pages_shared', 'pages_to_scan',
                            'pages_volatile',  'sleep_millisecs' ]
        self.open_files()

    def __del__(self):
        for datum in self.sysfs_keys:
            if datum in self.files and self.files[datum] is not None:
                self.files[datum].close()

    def open_files(self):
        self.files = {}
        for datum in self.sysfs_keys:
            name = '/sys/kernel/mm/ksm/%s' % datum
            try:
                self.files[datum] = open(name, 'r')
            except IOError as (errno, msg):
                raise FatalError("HostKSM: open %s failed: %s" % (name, msg))

    def get_shareable_mem(self):
        """
        Estimate how much memory has been reported to KSM for potential sharing.
        We assume that qemu is reporting guest physical memory areas to KSM.
        """
        p1 = Popen(["pgrep", "qemu"], stdout=PIPE).communicate()[0]
        pids = p1.split()
        if len(pids) == 0:
            return 0
        ps_argv = ["ps", "-ovsz", "h"] + pids
        p1 = Popen(ps_argv, stdout=PIPE).communicate()[0]
        mem_tot = 0
        for mem in p1.split():
            mem_tot = mem_tot + int(mem)
        return mem_tot

    def collect(self):
        data = {}
        for (datum, file) in self.files.items():
            file.seek(0)
            data['ksm_' + datum] = parse_int('(.*)', file.read())
        data['ksm_shareable'] = self.get_shareable_mem()
        return data

def instance(properties):
    return HostKSM(properties)
