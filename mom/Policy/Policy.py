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

import logging
from Parser import Evaluator
from Parser import get_code
from Parser import PolicyError

class Policy:
    def __init__(self, policy_string):
        self.logger = logging.getLogger('mom.Policy')
        self.policy_string = policy_string
        self.evaluator = Evaluator()
        self.code = get_code(self.evaluator, self.policy_string)

    def get_string(self):
        return self.policy_string

    def evaluate(self, host, guest_list):
        results = []
        self.evaluator.stack.set('Host', host, alloc=True)
        self.evaluator.stack.set('Guests', guest_list, alloc=True)
        
        try:
            for expr in self.code:
                results.append(self.evaluator.eval(expr))
            self.logger.debug("Results: %s" % results)
        except PolicyError as e:
            self.logger.error("Policy error: %s" % e)
            return False
        except Exception as e:
            self.logger.error("Unexpected error when evaluating policy: %s" % e)
            return False
        return True
