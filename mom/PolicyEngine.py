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
    def __init__(self, config, libvirt_iface, host_monitor, guest_manager):
        threading.Thread.__init__(self, name="PolicyEngine")
        self.setDaemon(True)
        self.config = config
        self.logger = logging.getLogger('mom.PolicyEngine')
        self.policy_sem = threading.Semaphore()
        self.properties = {
            'libvirt_iface': libvirt_iface,
            'host_monitor': host_monitor,
            'guest_manager': guest_manager,
        }

        policy_file = self.config.get('main', 'policy')
        policy_str = self.read_rules(policy_file)
        if policy_str is None:
            self.logger.error("Policy Engine initialization failed")
            return
        self.load_policy(policy_str)
        self.start()

    def read_rules(self, fname):
        if fname is None or fname == "":
            return ""
        try:
            f = open(fname, 'r')
            str = f.read()
            f.close()
        except IOError, e:
            self.logger.error("Unable to read policy file: %s" % e)
            return None
        return str

    def load_policy(self, str):
        ret = True
        if str is None or str == "":
            self.logger.warn('%s: No policy specified.', self.getName())
            str = "0" # XXX: Parser should accept an empty program

        try:
            new_pol = Policy(str)
        except:
            return False
        self.policy_sem.acquire()
        self.policy = new_pol
        self.policy_sem.release()
        return True

    def rpc_get_policy(self):
        self.policy_sem.acquire()
        if self.policy is not None:
            str = self.policy.get_string()
        else:
            str = ""
        self.policy_sem.release()
        return str

    def rpc_set_policy(self, str):
        return self.load_policy(str)

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
        
        self.policy_sem.acquire()
        ret = self.policy.evaluate(host, guest_list)            
        self.policy_sem.release()
        if ret is False:
            return
        for c in self.controllers:
            c.process(host, guest_list)

    def run(self):
        self.logger.info("Policy Engine starting")
        self.get_controllers()
        interval = self.config.getint('main', 'policy-engine-interval')
        while self.config.getint('__int__', 'running') == 1:
            time.sleep(interval)
            self.do_controls()
        self.logger.info("Policy Engine ending")

