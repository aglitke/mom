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

class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

class RPCServer(threading.Thread):
    """
    The RPCServer thread provides an API for external programs to interact
    with MOM.
    """
    def __init__(self, config, momFuncs):
        threading.Thread.__init__(self, name="RPCServer")
        self.setDaemon(True)
        self.config = config
        self.momFuncs = momFuncs
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
        self.server.register_instance(self.momFuncs)
    
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
