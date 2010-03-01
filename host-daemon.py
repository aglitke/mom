#! /usr/bin/env python

import signal
import time
from optparse import OptionParser
import ConfigParser
from MomUtils import *
from libvirtInterface import libvirtInterface
from HostMonitor import HostMonitor
from GuestManager import GuestManager
from Controllers.SystemController import SystemController
from Controllers.Rules import read_rules

config = None
def read_config(fname):
    global config
    config = ConfigParser.SafeConfigParser()
    # Set defaults
    config.add_section('main')
    config.set('main', 'main-loop-interval', '60')
    config.set('main', 'host-monitor-interval', '5')
    config.set('main', 'guest-manager-interval', '5')
    config.set('main', 'guest-monitor-interval', '5')
    config.set('main', 'system-controller-interval', '10')
    config.set('main', 'sample-history-length', '10')
    config.set('main', 'libvirt-hypervisor-uri', '')
    config.set('main', 'controllers', '')
    config.add_section('host')
    config.set('host', 'collectors', 'HostMemory')
    config.add_section('guest')
    config.set('guest', 'collectors', 'GuestQemuProc, GuestLibvirt')
    config.read(fname)

    # Add non-customizable thread-global variables
    config.set('main', 'running', '0')

def signal_quit(signum, frame):
    global config
    logger(LOG_INFO, "Received signal %i shutting down.", signum)
    config.set('main', 'running', '0')

def threads_ok(threads):
    """
    Check to make sure a list of expected threads are still alive
    """
    for t in threads:
        if not t.is_alive():
            return False
    return True

def main():
    global config

    cmdline = OptionParser()
    cmdline.add_option('-c', '--config-file', dest='config_file',
                       help='Load configuration from FILE', metavar='FILE',
                       default='/etc/mom.conf')
    cmdline.add_option('-r', '--rules-file', dest='rules_file',
                       help='Load rules from FILE', metavar='FILE',
                       default='')
    (options, args) = cmdline.parse_args()
    read_config(options.config_file)
    rules = read_rules(options.rules_file)

    signal.signal(signal.SIGINT, signal_quit)
    signal.signal(signal.SIGTERM, signal_quit)

    # Set up a shared libvirt connection
    uri = config.get('main', 'libvirt-hypervisor-uri')
    libvirt_iface = libvirtInterface(uri)

    # Start threads
    logger(LOG_DEBUG, "Daemon starting")
    config.set('main', 'running', '1')
    host_monitor = HostMonitor(config)
    guest_manager = GuestManager(config, libvirt_iface)
    system_controller = SystemController(config, rules, libvirt_iface, \
                            host_monitor, guest_manager)

    interval = config.getint('main', 'main-loop-interval')
    while config.getint('main', 'running') == 1:
        time.sleep(interval)
        if not threads_ok((host_monitor,guest_manager,system_controller)):
            config.set('main', 'running', '0')

    system_controller.join(10)
    guest_manager.join(5)
    host_monitor.join(5)
    logger(LOG_INFO, "Daemon ending")
    exit(0)

if __name__ == "__main__":
    main()
