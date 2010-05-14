import threading
import time
import sys
import re
import logging
from mom.libvirtInterface import libvirtInterface
from mom.GuestMonitor import GuestMonitor

class GuestManager(threading.Thread):
    """
    The GuestManager thread maintains a list of currently active guests on the
    system.  When a new guest is discovered, a new GuestMonitor is spawned.
    When GuestMonitors stop running, they are removed from the list.
    """
    def __init__(self, config, libvirt_iface):
        threading.Thread.__init__(self, name='GuestManager')
        self.Daemon = True
        self.config = config
        self.logger = logging.getLogger('mom.GuestManager')
        self.libvirt_iface = libvirt_iface
        self.guests = {}
        self.guests_sem = threading.Semaphore()
        self.start()

    def spawn_guest_monitors(self):
        """
        Get the list of running domains and spawn GuestMonitors for any guests
        we are not already tracking.  The GuestMonitor constructor might block
        so don't hold guests_sem while calling it.
        """
        libvirt_list = self.libvirt_iface.listDomainsID()
        if libvirt_list is None:
            return

        self.guests_sem.acquire()
        spawn_list = set(libvirt_list) - set(self.guests)
        self.guests_sem.release()
        for id in spawn_list:
            guest = GuestMonitor(self.config, id, self.libvirt_iface)
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

    def check_threads(self):
        """
        Check for stale and/or deceased threads and remove them.
        """
        domain_list = self.libvirt_iface.listDomainsID()
        self.guests_sem.acquire()
        for (id, thread) in self.guests.items():
            # Check if the domain has ended according to libvirt
            if id not in domain_list:
                del self.guests[id]
            # Check if the thread has died
            if not thread.isAlive():
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
            ret[id] = monitor.interrogate()
        self.guests_sem.release()
        return ret

    def run(self):
        self.logger.info("Guest Manager starting");
        interval = self.config.getint('main', 'guest-manager-interval')
        while self.config.getint('main', 'running') == 1:
            self.spawn_guest_monitors()
            self.check_threads()
            time.sleep(interval)
        self.wait_for_guest_monitors()
        self.logger.info("Guest Manager ending")
