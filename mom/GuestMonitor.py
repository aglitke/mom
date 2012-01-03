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

import threading
import ConfigParser
import time
import re
from subprocess import *
import logging
from mom.Monitor import Monitor
from mom.Collectors import Collector


class GuestMonitor(Monitor, threading.Thread):
    """
    A GuestMonitor thread collects and reports statistics about 1 running guest
    """
    def __init__(self, config, id, libvirt_iface):
        threading.Thread.__init__(self, name="guest:%s" % id)
        self.config = config
        self.logger = logging.getLogger('mom.GuestMonitor')
        self.libvirt_iface = libvirt_iface
        self.guest_domain = self.libvirt_iface.getDomainFromID(id)
        info = self.get_guest_info()
        if info is None:
            self.logger.error("Failed to get guest:%s information -- monitor "\
                    "can't start", id)
            return

        self.setName("GuestMonitor-%s" % info['name'])
        Monitor.__init__(self, config, self.getName())
        self.setDaemon(True)
        
        self.data_sem.acquire()
        self.properties.update(info)
        self.properties['id'] = id
        self.properties['libvirt_iface'] = libvirt_iface
        self.data_sem.release()
        collector_list = self.config.get('guest', 'collectors')
        self.collectors = Collector.get_collectors(collector_list,
                            self.properties, self.config)
        if self.collectors is None:
            self.logger.error("Guest Monitor initialization failed")
            return
        self.start()
                            
    def get_guest_info(self):
        """
        Collect some basic properties about this guest
        Returns: A dict of properties on success, None otherwise
        """
        if self.guest_domain is None:
            return None
        data = {}
        data['uuid'] = self.libvirt_iface.domainGetUUID(self.guest_domain)
        data['name'] = self.libvirt_iface.domainGetName(self.guest_domain)
        data['pid'] = self.get_guest_pid(data['uuid'])
        if None in data.values():
                return None                
        return data

    def run(self):
        self.logger.info("%s starting", self.getName())
        interval = self.config.getint('main', 'guest-monitor-interval')
        while self._should_run():
            self.collect()
            time.sleep(interval)
        self.logger.info("%s ending", self.getName())

    def get_guest_pid(self, uuid):
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

    def getGuestName(self):
        """
        Provide structured access to the guest name without calling libvirt.
        """
        try:
            return self.properties['name']
        except KeyError:
            return None
