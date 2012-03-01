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
import time
import sys
import re
import logging
from mom.GuestMonitor import GuestMonitor

class GuestManager(threading.Thread):
    """
    The GuestManager thread maintains a list of currently active guests on the
    system.  When a new guest is discovered, a new GuestMonitor is spawned.
    When GuestMonitors stop running, they are removed from the list.
    """
    def __init__(self, config, hypervisor_iface):
        threading.Thread.__init__(self, name='GuestManager')
        self.setDaemon(True)
        self.config = config
        self.hypervisor_iface = hypervisor_iface
        self.logger = logging.getLogger('mom.GuestManager')
        self.guests = {}
        self.guests_sem = threading.Semaphore()
        self.start()

    def spawn_guest_monitors(self, domain_list):
        """
        Get the list of running domains and spawn GuestMonitors for any guests
        we are not already tracking.  The GuestMonitor constructor might block
        so don't hold guests_sem while calling it.
        """
        self.guests_sem.acquire()
        spawn_list = set(domain_list) - set(self.guests)
        self.guests_sem.release()
        for id in spawn_list:
            info = self.hypervisor_iface.getVmInfo(id)
            if info is None:
                self.logger.error("Failed to get guest:%s information -- monitor "\
                    "can't start", id)
                continue
            guest = GuestMonitor(self.config, info, self.hypervisor_iface)
            if guest.isAlive():
                self.guests_sem.acquire()
                if id not in self.guests:
                    self.guests[id] = guest
                else:
                    del guest
                self.guests_sem.release()

    def wait_for_guest_monitors(self):
        """
        Wait for GuestMonitors to exit
        """
        while True:
            self.guests_sem.acquire()
            if len(self.guests) > 0:
                (id, thread) = self.guests.popitem()
            else:
                id = None
            self.guests_sem.release()
            if id is not None:
                thread.join(0)
            else:
                break

    def check_threads(self, domain_list):
        """
        Check for stale and/or deceased threads and remove them.
        """
        self.guests_sem.acquire()
        for (id, thread) in self.guests.items():
            # Check if the thread has died
            if not thread.isAlive():
                del self.guests[id]
            # Check if the domain has ended according to hypervisor interface
            elif id not in domain_list:
                thread.terminate()
                del self.guests[id]
        self.guests_sem.release()

    def interrogate(self):
        """
        Interrogate all active GuestMonitors
        Return: A dictionary of Entities, indexed by guest id
        """
        ret = {}
        self.guests_sem.acquire()
        for (id, monitor) in self.guests.items():
            entity = monitor.interrogate()
            if entity is not None:
                ret[id] = entity
        self.guests_sem.release()
        return ret

    def run(self):
        self.logger.info("Guest Manager starting");
        interval = self.config.getint('main', 'guest-manager-interval')
        while self.config.getint('__int__', 'running') == 1:
            domain_list = self.hypervisor_iface.getVmList()
            if domain_list is not None:
                self.spawn_guest_monitors(domain_list)
                self.check_threads(domain_list)
            time.sleep(interval)
        self.wait_for_guest_monitors()
        self.logger.info("Guest Manager ending")

    def rpc_get_active_guests(self):
        ret = []
        self.guests_sem.acquire()
        for (id, monitor) in self.guests.items():
            if monitor.isReady():
                name = monitor.getGuestName()
                if name is not None:
                    ret.append(name)
        self.guests_sem.release()
        return ret
