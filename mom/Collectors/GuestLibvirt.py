# Memory Overcommitment Manager
# Copyright (C) 2010 Adam Litke, IBM Corporation
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

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
    libvirt_stats = [ 'libvirt_state', 'libvirt_maxmem', 'libvirt_curmem' ]
    
    def getFields(self=None):
        return set(GuestLibvirt.mem_stats.values() + GuestLibvirt.libvirt_stats)
        
    def __init__(self, properties):
        self.iface = properties['libvirt_iface']
        self.domain = self.iface.getDomainFromID(properties['id'])
        self.logger = logging.getLogger('mom.Collectors.GuestLibvirt')
        self.memstats_available = True

    def stats_error(self, msg):
        """
        Only print stats interface errors one time when we first discover a
        problem.  Otherwise the log will be overrun with noise.
        """
        if self.memstats_available:
            self.logger.debug(msg)
        self.memstats_available = False

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
                self.stats_error('libvirt memoryStats() is not ready')
                return ret
            for (src, target) in self.mem_stats.items():
                ret[target] = info[src]
            self.memstats_available = True
        except AttributeError:
            self.stats_error('Memory stats API not available for guest')

        return ret
        
def instance(properties):
    return GuestLibvirt(properties)
