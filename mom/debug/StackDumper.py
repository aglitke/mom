import sys
import traceback
import logging

try:
    import threadframe
except:
    pass

class StackDumper():
    def __init__(self):
        self.logger = logging.getLogger('mom.debug.StackDumper')

    def dump(self):
        try:
            stacks = sys._current_frames()
        except AttributeError:
            try:
                stacks = threadframe.dict()
            except:
                self.logger.debug("Stack dumping not supported")
                return

        for (id, stack) in stacks.items():
            msg = "Stack trace for thread %i\n" % id
            msg = msg + ''.join(traceback.format_stack(stack))
            self.logger.debug(msg)
