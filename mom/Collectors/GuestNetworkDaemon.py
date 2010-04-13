#! /usr/bin/env python
import sys
import signal
import socket
import ConfigParser
import logger
from mom.Collectors.Collector import *
from mom.HostMemory import HostMemory

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
    data can be passed but the following stats are implemented:\
        total      - The total amount of available memory (kB)
        free       - The amount of free memory including some caches (kB)
        swap_in    - The amount of memory swapped in since the last collection (pages)
        swap_out   - The amount of memory swapped out since the last collection (pages)
    """
    def __init__(self, properties):
        self.ip = properties['collector_ip']
        self.port = properties['collector_port']
        socket.setdefaulttimeout(1)

    def collect(self):
        data = ""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((self.ip, self.port))
            sock_send(s, "stats")
            data = sock_receive(s)     
        except socket.error as e:
            return {}
        s.close()

        ret = {}
        for item in data.split(","):
            parts = item.split(":")
            ret[parts[0]] = int(parts[1])
        return ret
        
def instance(properties):
    return GuestNetworkDaemon(properties)

#
# Begin Server-side code that runs on the guest
#

def signal_quit(signum, frame):
    print "Received signal", signum, "shutting down."
    sys.exit(0)

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
        response = "total:%i,free:%i,swap_in:%i,swap_out:%i" % \
                (data['total'], data['free'], data['swap_in'], data['swap_out']) 
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

def main():
    """
    Executable code for running a network collector server on a guest.
    """
    signal.signal(signal.SIGINT, signal_quit)
    signal.signal(signal.SIGTERM, signal_quit)

    config = ConfigParser.ConfigParser()
    config.add_section('main')
    config.set('main', 'host', '')
    config.set('main', 'port', '8989')  
    config.set('main', 'min_free', '0.20')
    config.set('main', 'max_free', '0.50')  
    server = _Server(config)
    server.run()

if __name__ == "__main__":
    main()
