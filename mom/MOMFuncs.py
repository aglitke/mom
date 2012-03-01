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
import ConfigParser
import time
import logging
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

from LogUtils import *

class MOMFuncs(object):
    def __init__(self, config, threads):
        self.config = config
        self.threads = threads
        self.logger = logging.getLogger('mom.RPCServer')

    def ping(self):
        self.logger.info("ping()")
        return True

    def setPolicy(self, policy):
        self.logger.info("setPolicy()")
        self.logger.debug("New Policy:\n %s", policy)
        return self.threads['policy_engine'].rpc_set_policy(policy)

    def getPolicy(self):
        self.logger.info("getPolicy()")
        return self.threads['policy_engine'].rpc_get_policy()

    def setVerbosity(self, verbosity):
        self.logger.info("setVerbosity()")
        logger = logging.getLogger()
        log_set_verbosity(logger, verbosity)
        return True

    def getStatistics(self):
        host_stats = self.threads['host_monitor'].interrogate().statistics[0]
        guest_stats = {}
        guest_entities = self.threads['guest_manager'].interrogate().values()
        for entity in guest_entities:
            guest_stats[entity.properties['name']] = entity.statistics[0]
        ret = { 'host': host_stats, 'guests': guest_stats }
        return ret

    def getActiveGuests(self):
        self.logger.info("getActiveGuests()")
        return self.threads['guest_manager'].rpc_get_active_guests()
