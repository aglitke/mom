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
import logging
from Policy.Policy import Policy

class PolicyEngine(threading.Thread):
    """
    At a regular interval, this thread triggers system reconfiguration by
    sampling host and guest data, evaluating the policy and reporting the
    results to all enabled Controller plugins.
    """
    def __init__(self, config, policy_file, libvirt_iface, host_monitor, guest_manager):
        threading.Thread.__init__(self, name="PolicyEngine")
        self.setDaemon(True)
        self.config = config
        self.policy_string = self.read_rules(policy_file)
        self.logger = logging.getLogger('mom.PolicyEngine')
        if self.policy_string == "":
            self.logger.warn('%s: No policy specified.', self.getName())
            self.policy_string = "0" # XXX: Parser should accept an empty program
        self.properties = {
            'libvirt_iface': libvirt_iface,
            'host_monitor': host_monitor,
            'guest_manager': guest_manager,
        }
        self.start()

    def read_rules(self, fname):
        if fname is None or fname == "":
            return ""
        f = open(fname, 'r')
        str = f.read()
        f.close()
        return str

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
                module = __import__('mom.Controllers.' + name, None, None, name)
                self.logger.debug("Loaded %s controller", name)
            except ImportError:
                self.logger.warn("Unable to import controller: %s", name)
                continue
            self.controllers.append(module.instance(self.properties))

    def do_controls(self):
        """
        Sample host and guest data, process the rule set and feed the results
        into each configured Controller.
        """
        host = self.properties['host_monitor'].interrogate()
        if host is None:
            return
        guest_list = self.properties['guest_manager'].interrogate().values()
        if self.policy.evaluate(host, guest_list) is False:
            return
        for c in self.controllers:
            c.process(host, guest_list)

    def run(self):
        self.logger.info("Policy Engine starting")
        if self.policy_string is not None:
            self.policy = Policy(self.policy_string)
        self.get_controllers()
        interval = self.config.getint('main', 'policy-engine-interval')
        while self.config.getint('main', 'running') == 1:
            time.sleep(interval)
            self.do_controls()
        self.logger.info("Policy Engine ending")

