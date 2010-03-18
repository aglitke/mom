import threading
import time
import sys
import re
from MomUtils import *
from libvirtInterface import libvirtInterface
from GuestMonitor import GuestMonitor

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
        self.libvirt_iface = libvirt_iface
        self.guests = {}
        self.guests_sem = threading.Semaphore()
        self.start()

    def spawn_guest_monitors(self):
        """
        Get the list of running domains and spawn GuestMonitors for any guests
        we are not already tracking.  Remove any GuestMonitors that are no
        longer running.
        """
        dom_list = self.libvirt_iface.listDomainsID()
        if dom_list is None:
            return
        with self.guests_sem:
            for dom_id in dom_list:
                if dom_id not in self.guests:
                    logger(LOG_INFO, "GuestManager: Spawning Monitor for "\
                            "guest(%i)", dom_id)
                    self.guests[dom_id] = GuestMonitor(self.config, dom_id, \
                                                        self.libvirt_iface)
                elif not self.guests[dom_id].is_alive():
                    logger(LOG_INFO, "GuestManager: Cleaning up Monitor(%i)",\
                            dom_id)
                    self.guests[dom_id].join(2)
                    del self.guests[dom_id]

    def reap_old_guests(self):
        """
        Remove any GuestMonitors that no longer correspond to a running guest
        """
        domain_list = self.libvirt_iface.listDomainsID()
        if domain_list is None:
            return
        libvirt_doms = set(self.libvirt_iface.listDomainsID())
        with self.guests_sem:
            for dom_id in set(self.guests) - set(domain_list):
                del self.guests[dom_id]

    def wait_for_guest_monitors(self):
        """
        Wait for GuestMonitors to exit
        """
        with self.guests_sem:
            for dom_id in self.guests.keys():
                if self.guests[dom_id].is_alive():
                    self.guests[dom_id].join(2)

    def interrogate(self):
        """
        Interrogate all active GuestMonitors
        Return: A dictionary of Entities, indexed by guest id
        """
        ret = {}
        with self.guests_sem:
            for (id, monitor) in self.guests.items():
                ret[id] = monitor.interrogate()
        return ret

    def run(self):
        logger(LOG_INFO, "Guest Manager starting");
        interval = self.config.getint('main', 'guest-manager-interval')
        while self.config.getint('main', 'running') == 1:
            self.spawn_guest_monitors()
            self.reap_old_guests()
            time.sleep(interval)
        self.wait_for_guest_monitors()
        logger(LOG_INFO, "Guest Manager ending")
