#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import threading
import traceback


class Background(threading.Thread):
    """A class to allow background operation."""

    def __init__(self, o, m, a=None):
        """Create a thread to call o.m(a)."""

        threading.Thread.__init__(self)

        if not hasattr(o, m):
            raise RuntimeError("method missing from object")

        self._object = o
        self._method = m
        self._arguments = a
        self._exception = None
        self._traceback = None
        self._result = None

    def run(self):
        """Run o.m with arguments a in background."""

        task = getattr(self._object, self._method)

        try:
            if self._arguments:
                self._result = task(self._arguments)
            else:
                self._result = task()
        except Exception as e:
            self._traceback = traceback.format_exc()
            self._exception = e

    def get_traceback(self):
        return self._traceback

    def stop(self):
        """Rejoin the thread."""

        self.join()

        if self._exception:
            raise self._exception

        return self._result
