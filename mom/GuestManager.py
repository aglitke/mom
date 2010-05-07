import threading
import time
import sys
import re
import logging
from mom.MomThread import MomThread
from mom.libvirtInterface import libvirtInterface
from mom.GuestMonitor import GuestMonitor

class GuestManager(threading.Thread, MomThread):
    """
    The GuestManager thread maintains a list of currently active guests on the
    system.  When a new guest is discovered, a new GuestMonitor is spawned.
    When GuestMonitors stop running, they are removed from the list.
    """
    def __init__(self, config, libvirt_iface):
        threading.Thread.__init__(self, name='GuestManager')
        MomThread.__init__(self)
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
        we are not already tracking.  Remove any GuestMonitors that are no
        longer running.
        Returns: True if successful, False otherwise
        """
        dom_list = self.libvirt_iface.listDomainsID()
        if dom_list is None:
            return True
        self.guests_sem.acquire()
        for dom_id in dom_list:
            if dom_id not in self.guests:
                self.logger.info("GuestManager: Spawning Monitor for "\
                        "guest(%i)", dom_id)
                guest = GuestMonitor(self.config, dom_id, self.libvirt_iface)
                if guest.isAlive():
                    self.guests[dom_id] = guest
                else:
                    self.guests_sem.release()
                    return False
            elif not self.guests[dom_id].isAlive():
                self.logger.info("GuestManager: Cleaning up Monitor(%i)", \
                                 dom_id)
                self.guests[dom_id].join(2)
                del self.guests[dom_id]
        self.guests_sem.release()
        return True

    def reap_old_guests(self):
        """
        Remove any GuestMonitors that no longer correspond to a running guest
        """
        domain_list = self.libvirt_iface.listDomainsID()
        if domain_list is None:
            return
        libvirt_doms = set(self.libvirt_iface.listDomainsID())
        self.guests_sem.acquire()
        for dom_id in set(self.guests) - set(domain_list):
            del self.guests[dom_id]
        self.guests_sem.release()

    def wait_for_guest_monitors(self):
        """
        Wait for GuestMonitors to exit
        """
        self.guests_sem.acquire()
        for dom_id in self.guests.keys():
            if self.guests[dom_id].isAlive():
                self.guests[dom_id].join(2)
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

    def check_threads(self):
        """
        Check to make sure our GuestMonitors are responding.  Any threads that
        have stalled or are not responding will trigger log messages.
        """
        status = True
        now = time.time()
        interval = self.config.getint('main', 'guest-monitor-interval')
        self.guests_sem.acquire()
        for thread in self.guests.values():
            if not thread.check_thread(now, interval):
                status = False
        self.guests_sem.release()
        return status

    def run(self):
        self.logger.info("Guest Manager starting");
        interval = self.config.getint('main', 'guest-manager-interval')
        while self.config.getint('main', 'running') == 1:
            if not self.spawn_guest_monitors():
                self.logger.error("A problem occurred while spawning " \
                                  "GuestMonitors -- terminating")
                break
            self.reap_old_guests()
            self.interval_complete()
            if not self.check_threads():
                self.logger.error("GuestMonitor threads have failed -- terminating")
                break
            time.sleep(interval)
        self.wait_for_guest_monitors()
        self.logger.info("Guest Manager ending")
