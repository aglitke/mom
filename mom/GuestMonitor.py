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
        threading.Thread.__init__(self, name="GuestMonitor-%s" % id)
        Monitor.__init__(self, config, self.name)
        self.daemon = True
        self.config = config
        self.logger = logging.getLogger('mom.GuestMonitor')
        self.libvirt_iface = libvirt_iface
        self.properties['id'] = id
        self.properties['libvirt_iface'] = libvirt_iface

        if not self.get_guest_info():
            self.logger.error("Failed to get guest:%s information -- monitor "\
                    "can't start", self.properties['id'])
            return
        collector_list = self.config.get('guest', 'collectors')
        self.collectors = Collector.get_collectors(collector_list,
                            self.properties)
        if self.collectors is None:
            self.logger.error("Guest Monitor initialization failed")
            return
        self.start()
                            
    def get_guest_info(self):
        """
        Set up some basic guest properties
        Returns: True on success, False otherwise
        """
        id = self.properties['id']
        self.guest_domain = self.libvirt_iface.getDomainFromID(id)
        if self.guest_domain is None:
            return False
        uuid = self.libvirt_iface.domainGetUUID(self.guest_domain)
        name = self.libvirt_iface.domainGetName(self.guest_domain)
        pid = self.get_guest_pid(uuid)
        ip = self.get_guest_ip(name)
        for var in (uuid, name, pid):
            if var is None:
                return False
        with self.data_sem:
            self.properties['uuid'] = uuid
            self.properties['pid'] = pid
            self.properties['name'] = name
            self.properties['ip'] = ip
        return True

    def run(self):
        self.logger.info("%s starting", self.name)
        interval = self.config.getint('main', 'guest-monitor-interval')
        while self._should_run():
            if not self.libvirt_iface.domainIsRunning(self.guest_domain):
                break
            data = self.collect()
            time.sleep(interval)
        self.logger.info("%s ending", self.name)

    def get_guest_pid(self, uuid):
        """
        This is an ugly way to find the pid of the qemu process associated with
        this guest.  Scan ps output looking for our uuid and record the pid.
        Something is probably wrong if more or less than 1 match is returned.
        """
        p1 = Popen(["ps", "ax"], stdout=PIPE).communicate()[0]
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
        
    def get_guest_ip(self, name):
        """
        There is no simple, standardized way to determine a guest's IP address.
        We side-step the problem and make use of a helper program if specified.
        
        XXX: This is a security hole!  We are running a user-specified command!
        """
        if not self.config.has_option('guest', 'name-to-ip-helper'):
            return None
        prog = self.config.get('guest', 'name-to-ip-helper')
        try:
            output = Popen([prog, name], stdout=PIPE).communicate()[0]
        except OSError, (errno, strerror):
            self.logger.warn("Cannot call name-to-ip-helper: %s", strerror)
            return None
        matches = re.findall("^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
                             output, re.M)
        if len(matches) is not 1:
            self.logger.warn("Output from name-to-ip-helper %s is not an IP " \
                             "address. (output = '%s')", name, output)
            return None
        else:
            ip = matches[0]
            self.logger.debug("Guest %s has IP address %s", name, ip)
            return ip
