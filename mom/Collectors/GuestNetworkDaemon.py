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

import sys
import signal
import socket
from subprocess import *
import ConfigParser
import logging
from mom.Collectors.Collector import *
from mom.Collectors.HostMemory import HostMemory

def sock_send(conn, msg):
    """
    Send a message via a socket connection.  '\n' marks the end of the message.
    """
    msg = msg + "\n"
    sent = 0
    while sent < len(msg):
        ret = conn.send(msg[sent:])
        if ret == 0:
            raise socket.error("Unable to send on socket")
        sent = sent + ret

def sock_receive(conn, logger=None):
    """
    Receive a '\n' terminated message via a socket connection.
    """
    msg = ""
    done = False
    if logger:
        logger.debug('sock_receive(%s)' % conn)
    while not done:
        chunk = conn.recv(4096)
        if logger:
            logger.debug("sock_receive: received next chunk: %s" % repr(chunk))        
        if chunk == '':
            done = True
        msg = msg + chunk
        if msg[-1:] == '\n':
            done = True
    if len(msg) == 0:
        raise socket.error("Unable to receive on socket")
    else:
        return msg.rstrip("\n")

def sock_close(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
    except socket.error:
        pass

class GuestNetworkDaemon(Collector):
    """
    A guest memory stats Collector implemented over a socket connection.  Any
    data can be passed but the following stats are implemented:
        mem_available - The total amount of available memory (kB)
        mem_unused    - The amount of memory that is not being used for any purpose (kB)
        major_fault   - Total number of major page faults
        minor_fault   - Total number of minor page faults
        swap_in       - The amount of memory swapped in since the last collection (pages)
        swap_out      - The amount of memory swapped out since the last collection (pages)
    """
    
    def __init__(self, properties):
        self.logger = logging.getLogger('mom.Collectors.GuestNetworkDaemon')
        self.name = properties['name']
        self.ip = self.get_guest_ip(properties)
        self.port = 2187              # XXX: This needs to be configurable
        self.socket = None
        self.state = 'ok'

    def get_guest_ip(self, properties):
        """
        There is no simple, standardized way to determine a guest's IP address.
        We side-step the problem and make use of a helper program if specified.
        
        XXX: This is a security hole!  We are running a user-specified command!
        """
        name = properties['name']
        try:
            prog = properties['config']['name-to-ip-helper']
        except KeyError:
            return None
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

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.ip, self.port))
        except socket.error, msg:
            sock_close(self.socket)
            self.socket = None             
            raise CollectionError('Network connection to %s failed: %s' %
                                  (self.name, msg))

    def collect(self):
        if self.state == 'dead':
            return {}
        if self.ip is None:
            self.state = 'dead'
            raise CollectionError('No IP address for guest %s' % self.name)

        data = ""
        if self.socket is None:
            self.connect()
        try:
            sock_send(self.socket, "stats")
            data = sock_receive(self.socket, self.logger)
        except socket.error, msg:
            sock_close(self.socket)
            self.socket = None
            raise CollectionError('Network communication to %s failed: %s' %
                                  (self.name, msg))

        self.state = 'ok'

        # Parse the data string
        result = {}
        for item in data.split(","):
            parts = item.split(":")
            result[parts[0]] = int(parts[1])
        
        # Construct the return dict
        ret = {}
        for key in self.getFields():
            if key in result:
                ret[key] = result[key]
        return ret
        
    def getFields(self=None):
        return set(['mem_available', 'mem_unused', 'major_fault', 'minor_fault',
                    'swap_in', 'swap_out'])
        
def instance(properties):
    return GuestNetworkDaemon(properties)

#
# Begin Server-side code that runs on the guest
#

class _Server:
    """
    A simple TCP server that implements the guest side of the guest network
    Collector.
    """
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('mom.Collectors.GuestNetworkDaemon.Server')
        # Borrow a HostMemory Collector to get the needed data
        self.collector = HostMemory(None)
        self.vmstat = open_datafile("/proc/vmstat")

        # Socket Setup
        self.listen_ip = config.get('main', 'host')
        self.listen_port = config.getint('main', 'port')
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.listen_ip, self.listen_port))
        self.socket.listen(1)
        self.min_free = config.get('main', 'min_free')
        self.max_free = config.get('main', 'max_free')

    def __del__(self):
        sock_close(self.socket)
        if self.vmstat is not None:    
            self.vmstat.close()

    def send_props(self, conn):
        response = "min_free:" + self.min_free + ",max_free:" + self.max_free
        sock_send(conn, response)

    def send_stats(self, conn):
        data = self.collector.collect()
        self.vmstat.seek(0)
        contents = self.vmstat.read()
        minflt = parse_int("^pgfault (.*)", contents)
        majflt = parse_int("^pgmajfault (.*)", contents)

        response = "mem_available:%i,mem_unused:%i,swap_in:%i,swap_out:%i," \
                   "major_fault:%i,minor_fault:%i" % \
                   (data['mem_available'], data['mem_free'], data['swap_in'], \
                    data['swap_out'], majflt, minflt)
        sock_send(conn, response)

    def session(self, conn, addr):
        self.logger.debug("Connection received from %s", addr)
        conn.settimeout(10)
        while self.running:
            try:
                cmd = sock_receive(conn)
                if cmd == "props":
                    self.send_props(conn)
                elif cmd == "stats":
                    self.send_stats(conn)
                else:
                    break
            except socket.error, msg:
                self.logger.warn("Exception: %s" % msg)
                break
        sock_close(conn)
        self.logger.debug("Connection closed")

    def run(self):
        self.logger.info("Server starting")
        self.running = True
        while self.running:
            (conn, addr) = self.socket.accept()
            self.session(conn, addr)
        sock_close(self.socket)

