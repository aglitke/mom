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

class HypervisorInterface:
    """
    HypervisorInterface is an abstract class which defines all interfaces
    used by MOM to get guest memory statistics and control guest memory
    ballooning. Its sub classes libvirt and vdsm need implement all these
    interfaces by calling their respective API.
    """
    def getVmList(self):
        """
        This method returns a list, which is composed of the active guests'
        identifiers.
        """
        pass

    def getVmInfo(self, uuid):
        """
        This method returns basic information of a given guest, including
        name, uuid and pid.
        """
        pass

    def getVmMemoryStats(self, uuid):
        """
        This method returns the memory statistics of a given guest. The stat
        fields are decided by the real hypervisor interface.
        """
        pass

    def getVmBalloonInfo(self, uuid):
        """
        This method returns the balloon info a given guest, which includes two
        fields:
            balloon_max - The maximum amount of memory the guest may use
            balloon_cur - The current memory limit (set by ballooning)
        """
        pass

    def setVmBalloonTarget(self, uuid):
        """
        This method sets the balloon target of a given guest. It's used by the
        controller Balloon to inflate or deflate the balloon according to this
        guest's memory usage.
        """
        pass

    def ksmTune(self, tuningParams):
        """
        This method is used to set KSM tuning parameters by the controller KSM.
        """
        pass
