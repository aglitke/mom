import logging
import mom.libvirtInterface

class Balloon:
    """
    Simple Balloon Controller that uses the libvirt setMemory() API to resize
    a guest's memory balloon.  Output triggers are:
        - balloon_target - Set guest balloon to this size (kB)
    """
    def __init__(self, properties):
        self.libvirt_iface = properties['libvirt_iface']
        self.logger = logging.getLogger('mom.Controllers.Balloon')
        
    def process_guest(self, entities):
        target = entities['Output'].Var('balloon_target')
        if target is not None:
            target = int(target)
            id = entities['Guest'].Prop('id')
            prev_target = entities['Guest'].Stat('libvirt_curmem')
            self.logger.info("Ballooning guest:%s from %s to %s", \
                    id, prev_target, target)
            dom = self.libvirt_iface.getDomainFromID(id)
            if dom is not None:
                if self.libvirt_iface.domainSetBalloonTarget(dom, target):
                    self.logger.warn("Error while ballooning guest:%i", id)

def instance(properties):
    return Balloon(properties)
