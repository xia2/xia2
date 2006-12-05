#!/usr/bin/env python
# Decision.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.


#
# 13th June 2006
# 
# A handler for recording a list of all of the decisions and assertions.
# This will allow postmortem of what happened during the data processing,
# and should be allowed to print important decisions if desired - this 
# will require a special handler though.
# 
# 

import time
import copy

class _Decision:
    '''A handler for recording all of the decisions made.'''

    def __init__(self):
        self._decisions = []

        # the beginning of "time"
        self._construction_time = time.time()

        return

    def __del__(self):
        '''Print all of the decisions which were made.'''

        for d in self._decisions:
            print '[%10.2f] %s' % d

        return

    def record(self, decision):
        '''Record a decision for future reference.'''

        self._decisions.append((time.time() - self._construction_time,
                                decision))

        return

    def get(self):
        '''Get a list of all decisions made.'''

        return copy.deepcopy(self._decisions)

Decision = _Decision()

if __name__ == '__main__':
    
    Decision.record("I am a test")
    time.sleep(1)
    Decision.record("That was wrong")


    
