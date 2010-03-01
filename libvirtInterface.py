import libvirt
from MomUtils import *

class libvirtInterface:
    """
    libvirtInterface provides a wrapper for the libvirt API so that libvirt-
    related error handling can be consolidated in one place.  An instance of
    this class provides a single libvirt connection that can be shared by all
    threads.  If the connection is broken, an attempt will be made to reconnect.
    """
    def __init__(self, uri):
        self.conn = None
        self.uri = uri
        self._connect()

    def __del__(self):
        if self.conn is not None:
            self.conn.close()

    def _connect(self):
        try:
            self.conn = libvirt.open(self.uri)
        except libvirt.libvirtError as e:
            logger(LOG_ERROR, "libvirtInterface: error setting up " \
                    "connection: %s", e.message)
            
    def _reconnect(self):
        try:
            self.conn.close()
        except libvirt.libvirtError:
            pass # The connection is in a strange state so ignore these
        try:
            self._connect()
        except libvirt.libvirtError as e:
            logger(LOG_ERROR, 'libvirtInterface: Exception while reconnecting')

    def listDomainsID(self):
        try:
            dom_list = self.conn.listDomainsID()
        except libvirt.libvirtError as e:
            self.handleException(e)
            return []
        return dom_list

    def getDomainFromID(self, dom_id):
        try:
            dom = self.conn.lookupByID(dom_id)
        except libvirt.libvirtError as e:
            self.handleException(e)
            return None
        else:
            return dom
            
    def domainIsRunning(self, domain):
        try:
            if domain.info()[0] == libvirt.VIR_DOMAIN_RUNNING:
                return True
        except libvirt.libvirtError as e:
            self.handleException(e)
        return False
        
    def handleException(self, e):
        reconnect_errors = (libvirt.VIR_ERR_SYSTEM_ERROR,)
        error = e.get_error_code()
        if error in reconnect_errors:
            logger (LOG_WARN, 'libvirtInterface: connection lost, reconnecting.')
            self._reconnect()
        else:
            logger (LOG_WARN, 'libvirtInterface: Unhandled libvirt exception.')
