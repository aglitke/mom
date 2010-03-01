import threading
import time
from MomUtils import *

class SystemController(threading.Thread):
    """
    At a regular interval, this thread triggers system reconfiguration by
    sampling host and guest data, evaluating the rule set and reporting the
    results to all enabled Controller plugins.
    """
    def __init__(self, config, rules, libvirt_iface, host_monitor, guest_manager):
        threading.Thread.__init__(self, name="SystemController")
        self.daemon = True
        self.config = config
        self.rules = rules
        self.properties = {
            'libvirt_iface': libvirt_iface,
            'host_monitor': host_monitor,
            'guest_manager': guest_manager,
        }
        self.start()
    
    def get_controllers(self):
        """
        Initialize the Controllers called for in the config file.
        """
        self.controllers = []
        config_str = self.config.get('main', 'controllers')
        for name in config_str.split(','):
            name = name.lstrip()
            if name == '':
                continue
            try:
                module = __import__(name, None, None, name)
            except ImportError:
                logger("Unable to import controller: %s", name)
                continue
            self.controllers.append(module.instance(self.properties))

    def run(self):
        logger(LOG_INFO, "System Controller starting")
        self.get_controllers()
        interval = self.config.getint('main', 'system-controller-interval')
        while self.config.getint('main', 'running') == 1:
            time.sleep(interval)

        logger(LOG_INFO, "System Controller ending")


