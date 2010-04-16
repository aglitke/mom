#! /usr/bin/env python
import sys
import signal
import socket
import ConfigParser
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
            #logger.warn("Connection interrupted while sending")
            return
        sent = sent + ret

def sock_receive(conn):
    """
    Receive a '\n' terminated message via a socket connection.
    """
    msg = ""
    done = False
    while not done:
        chunk = conn.recv(4096)
        if chunk == '':
            done = True
        msg = msg + chunk
        if msg[-1:] == '\n':
            done = True
    return msg.rstrip("\n")

class GuestNetworkDaemon(Collector):
    """
    A guest memory stats Collector implemented over a socket connection.  Any
    data can be passed but the following stats are implemented:
        mem_available - The total amount of available memory (kB)
        mem_free      - The amount of free memory including some caches (kB)
        swap_in       - The amount of memory swapped in since the last collection (pages)
        swap_out      - The amount of memory swapped out since the last collection (pages)
    """
    
    def __init__(self, properties):
        self.ip = properties['ip']
        self.port = 2187              # XXX: This needs to be configurable
        self.name = properties['name']
        socket.setdefaulttimeout(1)
        self.state = 'ok'

    def collect(self):
        if self.state == 'dead':
            return {}
        if self.ip is None:
            self.state = 'dead'
            raise CollectionError('No IP address for guest %s' % self.name)

        data = ""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self.ip, self.port))
            sock_send(s, "stats")
            data = sock_receive(s)     
        except socket.error:
            if self.state != 'failing':
                self.state = 'failing'
                raise CollectionError('Nwtwork communication to %s failed' % \
                                      self.name)
            return {}
        s.close()
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
        return set(['mem_available', 'mem_free', 'swap_in', 'swap_out'])
        
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

        # Socket Setup
        self.listen_ip = config.get('main', 'host')
        self.listen_port = config.getint('main', 'port')
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.listen_ip, self.listen_port))
        self.socket.listen(1)
        
        self.min_free = config.get('main', 'min_free')
        self.max_free = config.get('main', 'max_free')

    def __del__(self):
        if self.socket is not None:
            self.socket.close()

    def send_props(self, conn):
        response = "min_free:" + self.min_free + ",max_free:" + self.max_free
        sock_send(conn, response)

    def send_stats(self, conn):
        data = self.collector.collect()
        response = "mem_available:%i,mem_free:%i,swap_in:%i,swap_out:%i" % \
                   (data['mem_available'], data['mem_free'], data['swap_in'], \
                    data['swap_out'])
        sock_send(conn, response)

    def run(self):
        while True:
            (conn, addr) = self.socket.accept()
            self.logger.debug("Connection received from %s", addr)
            cmd = sock_receive(conn)
            self.logger.debug("Got command %s", cmd)
            if cmd == "props":
                self.send_props(conn)
            elif cmd == "stats":
                self.send_stats(conn)
            conn.close()
