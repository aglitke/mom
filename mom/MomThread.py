import time
import sys
import traceback
import logging

class MomThread:
    def __init__(self):
        self.iter_complete_time = time.time()
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger('mom.MomThread')

    def get_last_interval_time(self):
        return self.iter_complete_time
    
    def interval_complete(self):
        self.iter_complete_time = time.time()

    def debug_thread_stack(self):
        for (id, stack) in sys._current_frames().items():
            if id != self.ident:
                continue
            msg = "Stack trace for thread %s\n" % self.name
            msg = msg + ''.join(traceback.format_stack(stack))
            self.logger.debug(msg)

    def check_thread(self, now, interval):
        if not self.isAlive():
            self.logger.error("Thread %s has unexepectedly quit", self.name)
            return False
        last_interval = self.get_last_interval_time()
        delay = now - last_interval
        if delay > 10 * interval:
            self.logger.error("Thread %s has stopped responding", self.name)
            return False
        if delay > 5 * interval:
            self.logger.warn("Thread %s has been stalled for %i seconds",
                        self.name, delay)
            if self.logger.isEnabledFor(logging.DEBUG):
                self.debug_thread_stack()
        return True
