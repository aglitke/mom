# Memory Overcommitment Manager
# Copyright (C) 2012 Mark Wu, IBM Corporation
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
class GuestBalloon(Collector):
    """
    This Collector uses hypervisor interface to collect guest balloon info
    """
    def getFields(self=None):
        return set(['balloon_cur', 'balloon_max'])

    def __init__(self, properties):
        self.hypervisor_iface = properties['hypervisor_iface']
        self.uuid = properties['uuid']
        self.logger = logging.getLogger('mom.Collectors.BalloonInfo')
        self.balloon_info_available = True

    def stats_error(self, msg):
        """
        Only print stats interface errors one time when we first discover a
        problem.  Otherwise the log will be overrun with noise.
        """
        if self.balloon_info_available:
            self.logger.debug(msg)
        self.balloon_info_available = False

    def collect(self):
        stat = self.hypervisor_iface.getVmBalloonInfo(self.uuid)
        if stat == None:
            self.stats_error('getVmBalloonInfo() is not ready')
        else:
            self.balloon_info_available = True
        return stat

def instance(properties):
    return GuestBalloon(properties)
