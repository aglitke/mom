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

import libvirt
import re
import logging
from subprocess import *
from mom.HypervisorInterfaces.HypervisorInterface import *

class libvirtInterface(HypervisorInterface):
    """
    libvirtInterface provides a wrapper for the libvirt API so that libvirt-
    related error handling can be consolidated in one place.  An instance of
    this class provides a single libvirt connection that can be shared by all
    threads.  If the connection is broken, an attempt will be made to reconnect.
    """
    def __init__(self, config):
        self.conn = None
        self.uri = config.get('main', 'libvirt-hypervisor-uri')
        self.logger = logging.getLogger('mom.libvirtInterface')
        libvirt.registerErrorHandler(self._error_handler, None)
        self._connect()
        self._setStatsFields()

    def __del__(self):
        if self.conn is not None:
            self.conn.close()

    # Older versions of the libvirt python bindings required an extra parameter.
    # Hence 'dummy'.
    def _error_handler(self, ctx, error, dummy=None):
        pass

    def _connect(self):
        try:
            self.conn = libvirt.open(self.uri)
        except libvirt.libvirtError, e:
            self.logger.error("libvirtInterface: error setting up " \
                    "connection: %s", e.message)

    def _reconnect(self):
        try:
            self.conn.close()
        except libvirt.libvirtError:
            pass # The connection is in a strange state so ignore these
        try:
            self._connect()
        except libvirt.libvirtError, e:
            self.logger.error("libvirtInterface: Exception while " \
                    "reconnecting: %s", e.message);


    def _getDomainFromID(self, dom_id):
        try:
            dom = self.conn.lookupByID(dom_id)
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        else:
            return dom

    def _getDomainFromUUID(self, dom_uuid):
        try:
            dom = self.conn.lookupByUUIDString(dom_uuid)
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        else:
            return dom

    def _domainIsRunning(self, domain):
        try:
            if domain.info()[0] == libvirt.VIR_DOMAIN_RUNNING:
                return True
        except libvirt.libvirtError, e:
            self._handleException(e)
        return False

    def _domainGetName(self, domain):
        try:
            name = domain.name()
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        return name

    def _domainGetUUID(self, domain):
        try:
            uuid = domain.UUIDString()
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        return uuid

    def _domainGetInfo(self, domain):
        try:
            info = domain.info()
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        return info

    def _domainGetPid(self, uuid):
        """
        This is an ugly way to find the pid of the qemu process associated with
        this guest.  Scan ps output looking for our uuid and record the pid.
        Something is probably wrong if more or less than 1 match is returned.
        """
        p1 = Popen(["ps", "axww"], stdout=PIPE).communicate()[0]
        matches = re.findall("^\s*(\d+)\s+.*" + uuid, p1, re.M)
        if len(matches) < 1:
            self.logger.warn("No matching process for domain with uuid %s", \
                             uuid)
            return None
        elif len(matches) > 1:
            self.logger.warn("Too many process matches for domain with uuid %s",\
                             uuid)
            return None
        return int(matches[0])


    def _domainGetMemoryStats(self, domain):
        try:
            stats = domain.memoryStats()
        except libvirt.libvirtError, e:
            self._handleException(e)
            return None
        return stats


    def _handleException(self, e):
        reconnect_errors = (libvirt.VIR_ERR_SYSTEM_ERROR,libvirt.VIR_ERR_INVALID_CONN)
        do_nothing_errors = (libvirt.VIR_ERR_NO_DOMAIN,)
        error = e.get_error_code()
        if error in reconnect_errors:
            self.logger.warn('libvirtInterface: connection lost, reconnecting.')
            self._reconnect()
        elif error in do_nothing_errors:
            pass
        else:
            self.logger.warn('libvirtInterface: Unhandled libvirt exception '\
                             '(%i).', error)

    def _domainSetBalloonTarget(self, domain, target):
        try:
            return domain.setMemory(target)
        except libvirt.libvirtError, e:
            self._handleException(e)
            return False

    def getVmList(self):
        try:
            dom_list = self.conn.listDomainsID()
        except libvirt.libvirtError, e:
            self._handleException(e)
            return []
        return dom_list

    def getVmInfo(self, id):
        data = {}
        guest_domain = self._getDomainFromID(id)
        data['uuid'] = self._domainGetUUID(guest_domain)
        data['name'] = self._domainGetName(guest_domain)
        data['pid'] = self._domainGetPid(data['uuid'])
        if None in data.values():
            return None
        return data

    def getVmMemoryStats(self, uuid):
        domain = self._getDomainFromUUID(uuid)
        # Try to collect memory stats.  This function may not be available
        info = self._domainGetMemoryStats(domain)
        ret = {}
        if info is None or len(info.keys()) == 0:
            self.logger.debug('libvirt memoryStats() is not active')
        for key in set(self.mem_stats.keys()) - set(info.keys()):
            ret[key] = info[key]
        return ret

    def _setStatsFields(self):
        """
        The following additional statistics may be available depending on the
        libvirt version, qemu version, and guest operation system version:
            mem_available - Total amount of memory available (kB)
            mem_unused - Amount of free memory not including caches (kB)
            major_fault - Total number of major page faults
            minor_fault - Total number of minor page faults
            swap_in - Total amount of memory swapped in (kB)
            swap_out - Total amount of memory swapped out (kB)
        """
        self.mem_stats = { 'available': 'mem_available', 'unused': 'mem_unused',
                      'major_fault': 'major_fault', 'minor_fault': 'minor_fault',
                      'swap_in': 'swap_in', 'swap_out': 'swap_out' }

    def getStatsFields(self):
        return set(self.mem_stats.values())

    def getVmBalloonInfo(self, uuid):
        domain = self._getDomainFromUUID(uuid)
        info = self._domainGetInfo(domain)
        if info is None:
            self.logger.error('Failed to get domain info')
            return None
        ret =  {'balloon_max': info[1], 'balloon_cur': info[2]}
        return ret

    def setVmBalloonTarget(self, uuid, target):
        dom = self._getDomainFromUUID(uuid)
        if dom is not None:
            if self._domainSetBalloonTarget(dom, target):
                name = self._domainGetName(dom)
                self.logger.warn("Error while ballooning guest:%i", name)

def instance(config):
    return libvirtInterface(config)
