from Monitor import Monitor
from Collectors import Collector
import threading
import ConfigParser
import time
import re
from subprocess import *
from MomUtils import *

def get_guest_pid(uuid):
    """
    This is an ugly way to find the pid of the qemu process associated with this
    guest.  Scan ps output looking for our uuid and record the pid.  Something
    is probably wrong if more or less than 1 match is returned.
    """
    p1 = Popen(["ps", "ax"], stdout=PIPE).communicate()[0]
    matches = re.findall("^\s*(\d+)\s+.*" + uuid, p1, re.M)
    if len(matches) < 1:
        logger(LOG_WARN, "No matching process for domain with uuid %s", uuid)
        return None
    elif len(matches) > 1:
        logger(LOG_WARN, "Too many process matches for domain with uuid %s",\
                uuid)
        return None
    return int(matches[0])

class GuestMonitor(Monitor, threading.Thread):
    """
    A GuestMonitor thread collects and reports statistics about 1 running guest
    """
    def __init__(self, config, id, libvirt_iface):
        threading.Thread.__init__(self, name="GuestMonitor-%s" % id)
        Monitor.__init__(self, config, self.name)
        self.daemon = True
        self.config = config
        self.libvirt_iface = libvirt_iface
        self.properties['id'] = id
        self.properties['libvirt_iface'] = libvirt_iface

        if not self.get_guest_info():
            logger(LOG_ERROR, "Failed to get guest:%s information -- monitor "\
                    "can't start", self.properties['id'])
            return
        collector_list = self.config.get('guest', 'collectors')
        self.collectors = Collector.get_collectors(collector_list,
                            self.properties)
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
        pid = get_guest_pid(uuid)
        for var in (uuid, name, pid):
            if var is None:
                return False
        with self.data_sem:
            self.properties['uuid'] = uuid
            self.properties['pid'] = pid
            self.properties['name'] = name
        return True

    def run(self):
        logger(LOG_INFO, "%s starting", self.name)
        interval = self.config.getint('main', 'guest-monitor-interval')
        while self.config.getint('main', 'running') == 1:
            if not self.libvirt_iface.domainIsRunning(self.guest_domain):
                break
            data = self.collect()
            time.sleep(interval)
        logger(LOG_INFO, "%s ending", self.name)

    
