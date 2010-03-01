from Collector import *

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
        libvirt_available - Total amount of memory available (kB)
        libvirt_unused - Amount of free memory not including caches (kB)
        libvirt_major_fault - Total number of major page faults
        libvirt_minor_fault - Total number of minor page faults
        libvirt_swap_in - Total amount of memory swapped in (kB)
        libvirt_swap_out - Total amount of memory swapped out (kB)
    """
        
    def __init__(self, properties):
        self.iface = properties['libvirt_iface']
        self.domain = self.iface.getDomainFromID(properties['id'])

    def collect(self):
        info = self.domain.info()        
        ret =  {
            'libvirt_state': info[0], 'libvirt_maxmem': info[1],
            'libvirt_curmem': info[2],
        }

        # Try to collect memory stats.  This function may not be available
        try:
            info = self.domain.memoryStats()
            for key in info.keys():
                ret['libvirt_' + key] = info[key]
        except AttributeError:
            print "Mem stats not available"

        return ret
        
def instance(properties):
    return GuestLibvirt(properties)
