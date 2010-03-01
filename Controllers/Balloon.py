import libvirt
import libvirtInterface
from MomUtils import *

class Balloon():
    """
    Simple Balloon Controller that uses the libvirt setMemory() API to resize
    a guest's memory balloon.  Output triggers are:
        - balloon_target - Set guest balloon to this size (kB)
    """
    def __init__(self, properties):
        self.libvirt_iface = properties['libvirt_iface']
        
    def process_guest(self, entities):
        
        target = int(entities['Output'].Var('balloon_target'))
        if target is not None:
            id = entities['Guest'].Prop('id')
            prev_target = entities['Guest'].Stat('libvirt_curmem')
            logger(LOG_INFO, "Ballooning guest:%s from %s to %s", \
                    id, prev_target, target)
            dom = self.libvirt_iface.getDomainFromID(id)
            if dom is not None:
                try:
                    ret = dom.setMemory(target)
                except libvirt.libvirtError as e:
                    logger("libvirt error while ballooning: %s", e.message)

def instance(properties):
    return Balloon(properties)
