# Memory Overcommitment Manager
# Copyright (C) 2011 Adam Litke, IBM Corporation
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

import sys
import signal
import socket
import ConfigParser
import logging
from mom.Collectors.Collector import *
from mom.Collectors.QemuGuestAgentClient import *

class GuestQemuAgent(Collector):
    """
    A guest memory stats Collector implemented as a standalone qemu-ga client.
        mem_available - The total amount of available memory (kB)
        mem_unused    - The amount of memory that is not being used for any purpose (kB)
        mem_free      - The amount of free memory including some caches (kB)
        major_fault   - Total number of major page faults
        minor_fault   - Total number of minor page faults
        swap_in       - The amount of memory swapped in since the last collection (pages)
        swap_out      - The amount of memory swapped out since the last collection (pages)
    """
    
    def __init__(self, properties):
        self.name = properties['name']
        
        try:
            socket_path = properties['config']['socket_path']
        except KeyError:
            socket_path = '/var/lib/libvirt/qemu'
        self.sockets = [ "%s/%s.agent" % (socket_path, self.name) ]
        self.agent = None
        self.logger = logging.getLogger('mom.Collectors.GuestQemuAgent')
        
        self.swap_in_prev = None
        self.swap_in_cur = None
        self.swap_out_prev = None
        self.swap_out_cur = None

    def agent_cmd(self, cmd, *args):
        """
        Wrap QemuGuestAgentClient calls to handle ProtocolErrors and return
        data in a standardized way.  Any error (Protocol or API) will result
        in a CollectionError being raised.
        """
        try:
            func = getattr(self.agent.api, cmd)
        except AttributeError:
            raise CollectionError("Invalid agent command: %s" % cmd)

        try:
            ret = func(*args)
        except ProtocolError, e:
            raise CollectionError("Agent communication failed: %s" % e)
        if ret.error:
            # Convert error data into a string of the form:
            #    "foo=bar, whiz=bang"
            details = reduce(lambda x, y: x + ", %s" % y, 
                             map(lambda x: "%s=%s" % x,
                                 ret.error['data'].items()))
            err_str = "%s (details: %s)" % (ret.error['class'], details)
            raise CollectionError("Agent command failed: %s" % err_str)

        return ret.data

    def connect(self):
        """
        Connect to the correct agent socket.  To transparently support both
        virtio-serial and isa-serial channels, we try two different socket files
        when connecting.  The client only attempts a connection when an API is
        actually called so try to ping the guest.  If this works then we know we
        have a usable connection.  If both sockets fail then report failure.
        """
        if self.agent is not None:
            return True

        for path in self.sockets:
            try:                
                agent = QemuGuestAgentClient(path)
                ret = agent.api.ping()
                if not ret.error:
                    self.agent = agent
                    break
            except Exception, e:
                self.logger.debug("Connection failed: %s" % e)
        return self.agent is not None

    def getfile(self, path):
        """
        Convenience function to fetch a whole file using open/read/close APIs
        """
        fh = self.agent_cmd('file_open', path, "r")
        data = ""
        while True:
            ret = self.agent_cmd('file_read', fh, 1024)
            data += ret['buf']
            if len(ret) < 1024:
                break
        self.agent_cmd('file_close', fh)
        return data

    def collect(self):
        if not self.connect():
            raise CollectionError('Unable to connect to agent')
        meminfo = self.getfile("/proc/meminfo")
        vmstat = self.getfile("/proc/vmstat")
        
        avail = parse_int("^MemTotal: (.*) kB", meminfo)
        anon = parse_int("^AnonPages: (.*) kB", meminfo)
        unused = parse_int("^MemFree: (.*) kB", meminfo)
        buffers = parse_int("^Buffers: (.*) kB", meminfo)
        cached = parse_int("^Cached: (.*) kB", meminfo)
        free = unused + buffers + cached

        # /proc/vmstat reports cumulative statistics so we must subtract the
        # previous values to get the difference since the last collection.
        minflt = parse_int("^pgfault (.*)", vmstat)
        majflt = parse_int("^pgmajfault (.*)", vmstat)
        self.swap_in_prev = self.swap_in_cur
        self.swap_out_prev = self.swap_out_cur
        self.swap_in_cur = parse_int("^pswpin (.*)", vmstat)
        self.swap_out_cur = parse_int("^pswpout (.*)", vmstat)
        if self.swap_in_prev is None:
            self.swap_in_prev = self.swap_in_cur
        if self.swap_out_prev is None:
            self.swap_out_prev = self.swap_out_cur
        swap_in = self.swap_in_cur - self.swap_in_prev
        swap_out = self.swap_out_cur - self.swap_out_prev

        data = { 'mem_available': avail, 'mem_unused': unused, \
                 'mem_free': free, 'swap_in': swap_in, 'swap_out': swap_out, \
                 'major_fault': majflt, 'minor_fault': minflt, }
        return data
        
    def getFields(self=None):
        return set(['mem_available', 'mem_unused', 'mem_free',
                    'major_fault', 'minor_fault', 'swap_in', 'swap_out'])
        
def instance(properties):
    return GuestQemuAgent(properties)
