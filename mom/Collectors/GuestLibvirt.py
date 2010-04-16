from mom.Collectors.Collector import *

class GuestLibvirt(Collector):
    """
    This Collector uses libvirt to return guest memory statistics
        libvirt_state - The domain state defined by libvirt as:
                VIR_DOMAIN_NOSTATE  = 0 : no state
                VIR_DOMAIN_RUNNING  = 1 : the domain is running
                VIR_DOMAIN_BLOCKED  = 2 : the domain is blocked on resource
                VIR_DOMAIN_PAUSED   = 3 : the domain is paused by user
                VIR_DOMAIN_SHUTDOWN = 4 : the domain is being shut down
                VIR_DOMAIN_SHUTOFF  = 5 : the domain is shut off
                VIR_DOMAIN_CRASHED  = 6 : the domain is crashed
        libvirt_maxmem - The maximum amount of memory the guest may use
        libvirt_curmem - The current memory limit (set by ballooning)
        
    The following additional statistics may be available depending on the
    libvirt version, qemu version, and guest operation system version:
        mem_available - Total amount of memory available (kB)
        mem_unused - Amount of free memory not including caches (kB)
        major_fault - Total number of major page faults
        minor_fault - Total number of minor page faults
        swap_in - Total amount of memory swapped in (kB)
        swap_out - Total amount of memory swapped out (kB)
    """
    mem_stats = { 'available': 'mem_available', 'unused': 'mem_unused',
                  'major_fault': 'major_fault', 'minor_fault': 'minor_fault',
                  'swap_in': 'swap_in', 'swap_out': 'swap_out' }
        
    def __init__(self, properties):
        self.iface = properties['libvirt_iface']
        self.domain = self.iface.getDomainFromID(properties['id'])
        self.logger = logging.getLogger('mom.Collectors.GuestLibvirt')

    def collect(self):
        info = self.iface.domainGetInfo(self.domain)
        if info is None:
            raise CollectionError('Failed to get domain info')

        ret =  {
            'libvirt_state': info[0], 'libvirt_maxmem': info[1],
            'libvirt_curmem': info[2],
        }

        # Try to collect memory stats.  This function may not be available
        try:
            info = self.iface.domainGetMemoryStats(self.domain)
            if info is None or len(info.keys()) == 0:
                self.logger.debug('libvirt memoryStats() is not ready')
                return ret
            for (src, target) in self.mem_stats.items():
                ret[target] = info[src]
        except AttributeError:
            self.logger.debug('Memory stats API not available for guest')

        return ret
        
def instance(properties):
    return GuestLibvirt(properties)
