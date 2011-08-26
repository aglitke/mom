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

class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

class RPCServer(threading.Thread):
    """
    The RPCServer thread provides an API for external programs to interact
    with MOM.
    """
    def __init__(self, config, host_monitor, guest_manager, policy_engine):
        threading.Thread.__init__(self, name="RPCServer")
        self.setDaemon(True)
        self.config = config
        self.threads = { 'host_monitor': host_monitor,
                         'guest_manager': guest_manager,
                         'policy_engine': policy_engine }
        self.logger = logging.getLogger('mom.RPCServer')
        self.server = None
        self.start()

    def thread_ok(self):
        if self.server is None:
            return True
        return self.isAlive()
    
    def create_server(self):
        try:
            port = self.config.getint('main', 'rpc-port')
        except ValueError:
            self.logger.error("Unable to parse 'rpc-port' configuration setting")
            return None
        if port is None or port < 0:
            return None
        self.server = SimpleXMLRPCServer(("localhost", port),
                            requestHandler=RequestHandler, logRequests=0)
        self.server.register_introspection_functions()
        self.server.register_instance(MOMFuncs(self.config, self.threads))
    
    def shutdown(self):
        if self.server is not None:
            self.server.shutdown()

    def run(self):
        self.create_server()
        if self.server is not None:
            self.logger.info("RPC Server starting")
            self.server.serve_forever()
            self.logger.info("RPC Server ending")
        else:
            self.logger.info("RPC Server is disabled")
