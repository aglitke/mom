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
import traceback
import logging

try:
    import threadframe
except:
    pass

class StackDumper:
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
