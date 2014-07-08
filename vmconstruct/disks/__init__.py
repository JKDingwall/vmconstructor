__all__ = []

import logging

class disks(object):
    def __init__(self, subvol, disksyml):
        self._logger = logging.getLogger(self.__class__.__module__+"."+self.__class__.__name__)
        self._disks = {}

        for (k, v) in disksyml:
            self._disks[k] = disk(subvol, k, v)



class disk(object):
    pass
